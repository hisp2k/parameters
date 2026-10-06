using System;
using System.Collections.Generic;
using System.Globalization;

namespace SolidWorksLocal
{
    // One circular cut in a constant-section profile. WallCount is one for an
    // angle leg and two for a through-both-walls cut in rectangular tube.
    internal sealed class ProfileHole
    {
        internal string Face;
        internal double AxialMm, EdgeOffsetMm, Diameter;
        internal int WallCount;
        internal double Radius { get { return Diameter / 2.0; } }
        internal ProfileHole(string face, double axialMm, double edgeOffsetMm, double diameter, int wallCount)
        {
            Face = face; AxialMm = axialMm; EdgeOffsetMm = edgeOffsetMm;
            Diameter = diameter; WallCount = wallCount;
        }
        internal object ToJson()
        {
            return Json.Obj("face", Face, "axial_mm", AxialMm, "edge_offset_mm", EdgeOffsetMm,
                "diameter_mm", Diameter, "wall_count", WallCount);
        }
    }

    internal sealed class ProfileHoleGroup
    {
        internal string Face, Pattern, Note;
        internal double Diameter, EdgeOffsetMm;
        internal readonly List<double> Positions = new List<double>();
        internal object ToJson()
        {
            return Json.Obj("face", Face, "pattern", Pattern, "diameter_mm", Diameter,
                "edge_offset_mm", EdgeOffsetMm, "positions_mm", Positions.ToArray(), "note", Note);
        }
    }

    // One axial obround slot in a flat profile wall. LengthMm is the overall
    // end-to-end slot length, WidthMm is the diameter of both semicircular caps.
    internal sealed class ProfileSlot
    {
        internal string Face;
        internal double AxialMm, EdgeOffsetMm, LengthMm, WidthMm;
        internal int WallCount;
        internal double Radius { get { return WidthMm / 2.0; } }
        internal double HalfLength { get { return LengthMm / 2.0; } }
        internal double StraightLength { get { return LengthMm - WidthMm; } }
        internal double AreaMm2 { get { return StraightLength * WidthMm + Math.PI * Radius * Radius; } }
        internal ProfileSlot(string face, double axialMm, double edgeOffsetMm,
            double lengthMm, double widthMm, int wallCount)
        {
            Face = face; AxialMm = axialMm; EdgeOffsetMm = edgeOffsetMm;
            LengthMm = lengthMm; WidthMm = widthMm; WallCount = wallCount;
        }
        internal object ToJson()
        {
            return Json.Obj("face", Face, "axial_mm", AxialMm,
                "edge_offset_mm", EdgeOffsetMm, "length_mm", LengthMm,
                "width_mm", WidthMm, "wall_count", WallCount);
        }
    }

    internal sealed class ProfileSlotGroup
    {
        internal string Face, Pattern, Note;
        internal double LengthMm, WidthMm, EdgeOffsetMm;
        internal readonly List<double> Positions = new List<double>();
        internal object ToJson()
        {
            return Json.Obj("face", Face, "pattern", Pattern,
                "length_mm", LengthMm, "width_mm", WidthMm,
                "edge_offset_mm", EdgeOffsetMm,
                "positions_mm", Positions.ToArray(), "note", Note);
        }
    }

    // Strict numeric language for stock with one constant cross-section.
    // v1 remains compatible with equal_angle. v2 adds rectangular_tube and
    // round_tube. v3 adds axial obround slots on flat angle/tube faces.
    // Rectangular-tube holes and slots pass through both opposite walls;
    // round-tube side cuts are deliberately not inferred from a PDF.
    internal sealed class ProfilePartPlan
    {
        internal const string BasicVersion = "1";
        internal const string TubeVersion = "2";
        internal const string CurrentVersion = "3";
        internal const double ClearanceMm = 0.05;

        internal string PlanVersion, MaterialName, CrossSectionType;
        internal double LegAMm, LegBMm, WidthMm, HeightMm;
        internal double OuterDiameterMm, InnerDiameterMm;
        internal double ThicknessMm, OuterCornerRadiusMm, InnerCornerRadiusMm;
        internal double LengthMm, CrossSectionAreaMm2, ExpectedVolumeM3;
        internal readonly List<ProfileHoleGroup> Groups = new List<ProfileHoleGroup>();
        internal readonly List<ProfileHole> Holes = new List<ProfileHole>();
        internal readonly List<ProfileSlotGroup> SlotGroups = new List<ProfileSlotGroup>();
        internal readonly List<ProfileSlot> Slots = new List<ProfileSlot>();
        internal NewPartProperties Properties;

        internal bool IsEqualAngle { get { return CrossSectionType == "equal_angle"; } }
        internal bool IsRectangularTube { get { return CrossSectionType == "rectangular_tube"; } }
        internal bool IsRoundTube { get { return CrossSectionType == "round_tube"; } }
        internal double EnvelopeWidthMm { get { return IsEqualAngle ? LegAMm : IsRectangularTube ? WidthMm : OuterDiameterMm; } }
        internal double EnvelopeHeightMm { get { return IsEqualAngle ? LegBMm : IsRectangularTube ? HeightMm : OuterDiameterMm; } }
        internal string ProfileTypeId
        {
            get
            {
                if (IsEqualAngle) return "equal_angle_extrusion";
                if (IsRectangularTube) return "rectangular_tube_extrusion";
                return "round_tube_extrusion";
            }
        }

        static void ExactKeys(Dictionary<string, object> value, string label, params string[] allowed)
        {
            var set = new HashSet<string>(allowed, StringComparer.Ordinal);
            foreach (string key in value.Keys)
                if (!set.Contains(key)) throw new Fault("INVALID_ARGUMENTS", label + " contains an unexpected field: " + key);
        }
        static string StringAt(Dictionary<string, object> value, string key)
        {
            string result = Json.At(value, key) as string;
            if (string.IsNullOrWhiteSpace(result)) throw new Fault("INVALID_ARGUMENTS", "Missing or invalid string: " + key);
            return result.Trim();
        }
        static double NumberAt(Dictionary<string, object> value, string key, double min, double max)
        {
            object raw = Json.At(value, key);
            if (!(raw is int || raw is long || raw is decimal || raw is double))
                throw new Fault("INVALID_ARGUMENTS", "Missing or invalid number: " + key);
            double result = Convert.ToDouble(raw, CultureInfo.InvariantCulture);
            if (double.IsNaN(result) || double.IsInfinity(result) || result < min || result > max)
                throw new Fault("INVALID_ARGUMENTS", key + " is out of range.");
            return result;
        }
        static double OptionalNumberAt(Dictionary<string, object> value, string key, double fallback, double min, double max)
        {
            if (!value.ContainsKey(key) || value[key] == null) return fallback;
            return NumberAt(value, key, min, max);
        }
        static int IntegerAt(Dictionary<string, object> values, string key, int min, int max)
        {
            double number = NumberAt(values, key, min, max);
            if (number != Math.Truncate(number)) throw new Fault("INVALID_ARGUMENTS", key + " must be an integer.");
            return (int)number;
        }
        static Array ArrayAt(Dictionary<string, object> value, string key, bool required)
        {
            object raw = Json.At(value, key);
            if (raw == null && !required) return new object[0];
            Array result = raw as Array;
            if (result == null) throw new Fault("INVALID_ARGUMENTS", key + " must be an array.");
            return result;
        }
        static Dictionary<string, object> ObjectAt(Dictionary<string, object> value, string key)
        {
            var result = Json.At(value, key) as Dictionary<string, object>;
            if (result == null) throw new Fault("INVALID_ARGUMENTS", key + " must be an object.");
            return result;
        }
        static string SafeTextAt(Dictionary<string, object> value, string key)
        {
            object raw = Json.At(value, key);
            if (raw == null) return null;
            string result = raw as string;
            if (string.IsNullOrWhiteSpace(result) || result.Length > 120)
                throw new Fault("INVALID_ARGUMENTS", key + " must contain 1 to 120 characters.");
            foreach (char c in result)
                if (char.IsControl(c)) throw new Fault("INVALID_ARGUMENTS", key + " cannot contain control characters.");
            return result.Trim();
        }
        static string SafeNoteAt(Dictionary<string, object> value, string key)
        {
            object raw = Json.At(value, key);
            if (raw == null) return null;
            string result = raw as string;
            if (result == null || result.Length > 400)
                throw new Fault("INVALID_ARGUMENTS", key + " must be a string of at most 400 characters.");
            foreach (char c in result)
                if (char.IsControl(c) && c != '\n' && c != '\r')
                    throw new Fault("INVALID_ARGUMENTS", key + " cannot contain control characters.");
            return result;
        }

        double FaceSpanFor(string face)
        {
            if (IsEqualAngle)
            {
                if (face == "leg_a") return LegAMm;
                if (face == "leg_b") return LegBMm;
                throw new Fault("INVALID_ARGUMENTS", "For equal_angle, face must be leg_a or leg_b.");
            }
            if (IsRectangularTube)
            {
                if (face == "face_a") return WidthMm;
                if (face == "face_b") return HeightMm;
                throw new Fault("INVALID_ARGUMENTS", "For rectangular_tube, face must be face_a or face_b.");
            }
            throw new Fault("INVALID_ARGUMENTS", "round_tube does not support hole_groups in plan_version=2.");
        }

        int WallCountFor(string face)
        {
            FaceSpanFor(face);
            return IsRectangularTube ? 2 : 1;
        }

        void AddHole(ProfileHole hole)
        {
            double span = FaceSpanFor(hole.Face);
            double required = hole.Radius + ClearanceMm;
            if (hole.AxialMm < required || hole.AxialMm > LengthMm - required)
                throw new Fault("INVALID_ARGUMENTS", "A hole on " + hole.Face + " falls outside the part length with 0.05 mm clearance.");

            double cornerMargin = IsRectangularTube ? OuterCornerRadiusMm : 0.0;
            if (hole.EdgeOffsetMm < cornerMargin + required ||
                hole.EdgeOffsetMm > span - cornerMargin - required)
                throw new Fault("INVALID_ARGUMENTS", "A hole on " + hole.Face + " leaves the verified planar face or its edge clearance.");

            foreach (ProfileHole existing in Holes)
            {
                if (existing.Face == hole.Face)
                {
                    double dx = existing.AxialMm - hole.AxialMm;
                    double dy = existing.EdgeOffsetMm - hole.EdgeOffsetMm;
                    double distance = Math.Sqrt(dx * dx + dy * dy);
                    if (distance < existing.Radius + hole.Radius + ClearanceMm)
                        throw new Fault("INVALID_ARGUMENTS", "Two holes on " + hole.Face + " overlap or touch.");
                }
                else if (IsRectangularTube &&
                    Math.Abs(existing.AxialMm - hole.AxialMm) <
                    existing.Radius + hole.Radius + ClearanceMm)
                {
                    // face_a and face_b cylinders are perpendicular and cross
                    // inside the tube envelope. Their shortest axis distance is
                    // the difference between their axial positions.
                    throw new Fault("INVALID_ARGUMENTS",
                        "Perpendicular rectangular-tube holes overlap or touch; their volume cannot be counted independently.");
                }
            }
            if (Holes.Count >= 256) throw new Fault("INVALID_ARGUMENTS", "At most 256 holes are allowed across all hole groups.");
            Holes.Add(hole);
        }

        void AddSlot(ProfileSlot slot)
        {
            double span = FaceSpanFor(slot.Face);
            if (slot.AxialMm < slot.HalfLength + ClearanceMm ||
                slot.AxialMm > LengthMm - slot.HalfLength - ClearanceMm)
                throw new Fault("INVALID_ARGUMENTS", "A slot on " + slot.Face +
                    " falls outside the part length with 0.05 mm clearance.");

            double cornerMargin = IsRectangularTube ? OuterCornerRadiusMm : 0.0;
            if (slot.EdgeOffsetMm < cornerMargin + slot.Radius + ClearanceMm ||
                slot.EdgeOffsetMm > span - cornerMargin - slot.Radius - ClearanceMm)
                throw new Fault("INVALID_ARGUMENTS", "A slot on " + slot.Face +
                    " leaves the verified planar face or its edge clearance.");

            foreach (ProfileHole hole in Holes)
            {
                double axialGap = Math.Abs(hole.AxialMm - slot.AxialMm);
                if (hole.Face == slot.Face)
                {
                    double edgeGap = Math.Abs(hole.EdgeOffsetMm - slot.EdgeOffsetMm);
                    if (axialGap < hole.Radius + slot.HalfLength + ClearanceMm &&
                        edgeGap < hole.Radius + slot.Radius + ClearanceMm)
                        throw new Fault("INVALID_ARGUMENTS", "A hole and slot on " +
                            slot.Face + " overlap or touch.");
                }
                else if (IsRectangularTube &&
                    axialGap < hole.Radius + slot.HalfLength + ClearanceMm)
                    throw new Fault("INVALID_ARGUMENTS",
                        "Perpendicular rectangular-tube hole and slot cuts overlap or touch.");
            }

            foreach (ProfileSlot existing in Slots)
            {
                double axialGap = Math.Abs(existing.AxialMm - slot.AxialMm);
                if (existing.Face == slot.Face)
                {
                    double edgeGap = Math.Abs(existing.EdgeOffsetMm - slot.EdgeOffsetMm);
                    if (axialGap < existing.HalfLength + slot.HalfLength + ClearanceMm &&
                        edgeGap < existing.Radius + slot.Radius + ClearanceMm)
                        throw new Fault("INVALID_ARGUMENTS", "Two slots on " +
                            slot.Face + " overlap or touch.");
                }
                else if (IsRectangularTube &&
                    axialGap < existing.HalfLength + slot.HalfLength + ClearanceMm)
                    throw new Fault("INVALID_ARGUMENTS",
                        "Perpendicular rectangular-tube slot cuts overlap or touch.");
            }
            if (Slots.Count >= 256)
                throw new Fault("INVALID_ARGUMENTS", "At most 256 slots are allowed across all slot groups.");
            Slots.Add(slot);
        }

        static double RoundedRectangleArea(double width, double height, double radius)
        {
            return width * height - (4.0 - Math.PI) * radius * radius;
        }

        internal static ProfilePartPlan Parse(Dictionary<string, object> args)
        {
            if (args == null) throw new Fault("INVALID_ARGUMENTS", "arguments must be an object.");
            ExactKeys(args, "profile part plan", "plan_version", "cross_section", "length_mm",
                "hole_groups", "slot_groups", "properties", "material");
            var plan = new ProfilePartPlan { PlanVersion = StringAt(args, "plan_version") };
            if (plan.PlanVersion != BasicVersion && plan.PlanVersion != TubeVersion &&
                plan.PlanVersion != CurrentVersion)
                throw new Fault("INVALID_ARGUMENTS", "Unsupported profile-part plan version. Use plan_version=1, 2 or 3.");

            Dictionary<string, object> crossSection = ObjectAt(args, "cross_section");
            plan.CrossSectionType = StringAt(crossSection, "type");

            if (plan.CrossSectionType == "equal_angle")
            {
                ExactKeys(crossSection, "equal_angle cross_section", "type", "leg_a_mm", "leg_b_mm", "thickness_mm");
                plan.LegAMm = NumberAt(crossSection, "leg_a_mm", 5.0, 1000.0);
                plan.LegBMm = NumberAt(crossSection, "leg_b_mm", 5.0, 1000.0);
                plan.ThicknessMm = NumberAt(crossSection, "thickness_mm", 0.5, 200.0);
                if (plan.ThicknessMm + 1.0 > plan.LegAMm || plan.ThicknessMm + 1.0 > plan.LegBMm)
                    throw new Fault("INVALID_ARGUMENTS", "thickness_mm must leave at least 1 mm of each leg beyond the corner overlap.");
                plan.CrossSectionAreaMm2 = plan.ThicknessMm * (plan.LegAMm + plan.LegBMm - plan.ThicknessMm);
            }
            else if (plan.CrossSectionType == "rectangular_tube")
            {
                if (plan.PlanVersion == BasicVersion)
                    throw new Fault("INVALID_ARGUMENTS", "rectangular_tube requires plan_version=2 or 3.");
                ExactKeys(crossSection, "rectangular_tube cross_section", "type", "width_mm", "height_mm",
                    "wall_thickness_mm", "outer_corner_radius_mm", "inner_corner_radius_mm");
                plan.WidthMm = NumberAt(crossSection, "width_mm", 5.0, 1000.0);
                plan.HeightMm = NumberAt(crossSection, "height_mm", 5.0, 1000.0);
                plan.ThicknessMm = NumberAt(crossSection, "wall_thickness_mm", 0.5, 200.0);
                if (2.0 * plan.ThicknessMm + 1.0 > Math.Min(plan.WidthMm, plan.HeightMm))
                    throw new Fault("INVALID_ARGUMENTS", "wall_thickness_mm must leave an inner opening of at least 1 mm.");
                double maxOuter = Math.Min(plan.WidthMm, plan.HeightMm) / 2.0 - ClearanceMm;
                double innerWidth = plan.WidthMm - 2.0 * plan.ThicknessMm;
                double innerHeight = plan.HeightMm - 2.0 * plan.ThicknessMm;
                double maxInner = Math.Min(innerWidth, innerHeight) / 2.0 - ClearanceMm;
                plan.OuterCornerRadiusMm = OptionalNumberAt(crossSection, "outer_corner_radius_mm", 0.0, 0.0, maxOuter);
                plan.InnerCornerRadiusMm = OptionalNumberAt(crossSection, "inner_corner_radius_mm", 0.0, 0.0, maxInner);
                bool sharp = plan.OuterCornerRadiusMm == 0.0 && plan.InnerCornerRadiusMm == 0.0;
                bool constantWallRadii = plan.OuterCornerRadiusMm >= plan.ThicknessMm &&
                    Math.Abs(plan.InnerCornerRadiusMm - (plan.OuterCornerRadiusMm - plan.ThicknessMm)) <= 1e-6;
                if (!sharp && !constantWallRadii)
                    throw new Fault("INVALID_ARGUMENTS", "Rounded rectangular_tube requires inner_corner_radius_mm = outer_corner_radius_mm - wall_thickness_mm. Omit both radii for sharp corners.");
                double outerArea = RoundedRectangleArea(plan.WidthMm, plan.HeightMm, plan.OuterCornerRadiusMm);
                double innerArea = RoundedRectangleArea(innerWidth, innerHeight, plan.InnerCornerRadiusMm);
                plan.CrossSectionAreaMm2 = outerArea - innerArea;
            }
            else if (plan.CrossSectionType == "round_tube")
            {
                if (plan.PlanVersion == BasicVersion)
                    throw new Fault("INVALID_ARGUMENTS", "round_tube requires plan_version=2 or 3.");
                ExactKeys(crossSection, "round_tube cross_section", "type", "outer_diameter_mm", "wall_thickness_mm");
                plan.OuterDiameterMm = NumberAt(crossSection, "outer_diameter_mm", 2.0, 2000.0);
                plan.ThicknessMm = NumberAt(crossSection, "wall_thickness_mm", 0.2, 500.0);
                plan.InnerDiameterMm = plan.OuterDiameterMm - 2.0 * plan.ThicknessMm;
                if (plan.InnerDiameterMm < 1.0)
                    throw new Fault("INVALID_ARGUMENTS", "wall_thickness_mm must leave an inner diameter of at least 1 mm.");
                plan.CrossSectionAreaMm2 = Math.PI *
                    (plan.OuterDiameterMm * plan.OuterDiameterMm - plan.InnerDiameterMm * plan.InnerDiameterMm) / 4.0;
            }
            else
            {
                throw new Fault("INVALID_ARGUMENTS", "cross_section.type must be equal_angle, rectangular_tube or round_tube.");
            }

            plan.LengthMm = NumberAt(args, "length_mm", 10.0, 12000.0);

            Array rawGroups = ArrayAt(args, "hole_groups", false);
            if (rawGroups.Length > 16) throw new Fault("INVALID_ARGUMENTS", "At most 16 hole groups are allowed.");
            if (plan.IsRoundTube && rawGroups.Length != 0)
                throw new Fault("INVALID_ARGUMENTS", "round_tube hole_groups are not supported because a circumferential datum is required.");

            foreach (object rawGroup in rawGroups)
            {
                var value = rawGroup as Dictionary<string, object>;
                if (value == null) throw new Fault("INVALID_ARGUMENTS", "Each hole group must be an object.");
                string pattern = StringAt(value, "pattern");
                var group = new ProfileHoleGroup { Face = StringAt(value, "face"), Pattern = pattern };
                int wallCount = plan.WallCountFor(group.Face);
                if (pattern == "linear")
                {
                    ExactKeys(value, "linear hole group", "face", "pattern", "diameter_mm", "edge_offset_mm", "start_mm", "count", "pitch_mm", "note");
                    group.Diameter = NumberAt(value, "diameter_mm", 0.2, 500.0);
                    group.EdgeOffsetMm = NumberAt(value, "edge_offset_mm", 0.0, 1000.0);
                    double start = NumberAt(value, "start_mm", -1000.0, 12000.0);
                    int count = IntegerAt(value, "count", 2, 256);
                    double pitch = NumberAt(value, "pitch_mm", 0.001, 12000.0);
                    if (pitch < group.Diameter + ClearanceMm)
                        throw new Fault("INVALID_ARGUMENTS", "Linear hole-group pitch must exceed the hole diameter by 0.05 mm.");
                    group.Note = SafeNoteAt(value, "note");
                    for (int i = 0; i < count; i++)
                    {
                        double axial = start + i * pitch;
                        group.Positions.Add(axial);
                        plan.AddHole(new ProfileHole(group.Face, axial, group.EdgeOffsetMm, group.Diameter, wallCount));
                    }
                }
                else if (pattern == "explicit")
                {
                    ExactKeys(value, "explicit hole group", "face", "pattern", "diameter_mm", "edge_offset_mm", "positions_mm", "count", "note");
                    group.Diameter = NumberAt(value, "diameter_mm", 0.2, 500.0);
                    group.EdgeOffsetMm = NumberAt(value, "edge_offset_mm", 0.0, 1000.0);
                    Array rawPositions = ArrayAt(value, "positions_mm", true);
                    if (rawPositions.Length < 1 || rawPositions.Length > 256)
                        throw new Fault("INVALID_ARGUMENTS", "explicit hole group requires 1 to 256 positions_mm.");
                    int declaredCount = IntegerAt(value, "count", 1, 256);
                    if (declaredCount != rawPositions.Length)
                        throw new Fault("INVALID_ARGUMENTS", "count must equal the number of positions_mm entries.");
                    group.Note = SafeNoteAt(value, "note");
                    double previous = double.NegativeInfinity;
                    foreach (object rawPosition in rawPositions)
                    {
                        if (!(rawPosition is int || rawPosition is long || rawPosition is decimal || rawPosition is double))
                            throw new Fault("INVALID_ARGUMENTS", "Every positions_mm entry must be a number.");
                        double axial = Convert.ToDouble(rawPosition, CultureInfo.InvariantCulture);
                        if (double.IsNaN(axial) || double.IsInfinity(axial))
                            throw new Fault("INVALID_ARGUMENTS", "Every positions_mm entry must be finite.");
                        if (axial < previous + group.Diameter + ClearanceMm)
                            throw new Fault("INVALID_ARGUMENTS", "positions_mm must be strictly ascending and non-overlapping.");
                        previous = axial;
                        group.Positions.Add(axial);
                        plan.AddHole(new ProfileHole(group.Face, axial, group.EdgeOffsetMm, group.Diameter, wallCount));
                    }
                }
                else
                {
                    throw new Fault("INVALID_ARGUMENTS", "hole_groups[].pattern must be linear or explicit.");
                }
                plan.Groups.Add(group);
            }

            Array rawSlotGroups = ArrayAt(args, "slot_groups", false);
            if (rawSlotGroups.Length > 16)
                throw new Fault("INVALID_ARGUMENTS", "At most 16 slot groups are allowed.");
            if (rawSlotGroups.Length != 0 && plan.PlanVersion != CurrentVersion)
                throw new Fault("INVALID_ARGUMENTS", "slot_groups require plan_version=3.");
            if (plan.IsRoundTube && rawSlotGroups.Length != 0)
                throw new Fault("INVALID_ARGUMENTS", "round_tube slot_groups are not supported because a circumferential datum is required.");

            foreach (object rawGroup in rawSlotGroups)
            {
                var value = rawGroup as Dictionary<string, object>;
                if (value == null) throw new Fault("INVALID_ARGUMENTS", "Each slot group must be an object.");
                string pattern = StringAt(value, "pattern");
                var group = new ProfileSlotGroup { Face = StringAt(value, "face"), Pattern = pattern };
                int wallCount = plan.WallCountFor(group.Face);
                group.LengthMm = NumberAt(value, "length_mm", 0.3, 2000.0);
                group.WidthMm = NumberAt(value, "width_mm", 0.2, 500.0);
                if (group.LengthMm < group.WidthMm + ClearanceMm)
                    throw new Fault("INVALID_ARGUMENTS", "A profile slot length_mm must exceed width_mm by at least 0.05 mm.");
                group.EdgeOffsetMm = NumberAt(value, "edge_offset_mm", 0.0, 1000.0);
                group.Note = SafeNoteAt(value, "note");

                if (pattern == "linear")
                {
                    ExactKeys(value, "linear slot group", "face", "pattern", "length_mm",
                        "width_mm", "edge_offset_mm", "start_mm", "count", "pitch_mm", "note");
                    double start = NumberAt(value, "start_mm", -1000.0, 12000.0);
                    int count = IntegerAt(value, "count", 2, 256);
                    double pitch = NumberAt(value, "pitch_mm", 0.001, 12000.0);
                    if (pitch < group.LengthMm + ClearanceMm)
                        throw new Fault("INVALID_ARGUMENTS", "Linear slot-group pitch must exceed the slot length by 0.05 mm.");
                    for (int i = 0; i < count; i++)
                    {
                        double axial = start + i * pitch;
                        group.Positions.Add(axial);
                        plan.AddSlot(new ProfileSlot(group.Face, axial, group.EdgeOffsetMm,
                            group.LengthMm, group.WidthMm, wallCount));
                    }
                }
                else if (pattern == "explicit")
                {
                    ExactKeys(value, "explicit slot group", "face", "pattern", "length_mm",
                        "width_mm", "edge_offset_mm", "positions_mm", "count", "note");
                    Array rawPositions = ArrayAt(value, "positions_mm", true);
                    if (rawPositions.Length < 1 || rawPositions.Length > 256)
                        throw new Fault("INVALID_ARGUMENTS", "explicit slot group requires 1 to 256 positions_mm.");
                    int declaredCount = IntegerAt(value, "count", 1, 256);
                    if (declaredCount != rawPositions.Length)
                        throw new Fault("INVALID_ARGUMENTS", "count must equal the number of positions_mm entries.");
                    double previous = double.NegativeInfinity;
                    foreach (object rawPosition in rawPositions)
                    {
                        if (!(rawPosition is int || rawPosition is long || rawPosition is decimal || rawPosition is double))
                            throw new Fault("INVALID_ARGUMENTS", "Every slot positions_mm entry must be a number.");
                        double axial = Convert.ToDouble(rawPosition, CultureInfo.InvariantCulture);
                        if (double.IsNaN(axial) || double.IsInfinity(axial))
                            throw new Fault("INVALID_ARGUMENTS", "Every slot positions_mm entry must be finite.");
                        if (axial < previous + group.LengthMm + ClearanceMm)
                            throw new Fault("INVALID_ARGUMENTS", "Slot positions_mm must be strictly ascending and non-overlapping.");
                        previous = axial;
                        group.Positions.Add(axial);
                        plan.AddSlot(new ProfileSlot(group.Face, axial, group.EdgeOffsetMm,
                            group.LengthMm, group.WidthMm, wallCount));
                    }
                }
                else
                {
                    throw new Fault("INVALID_ARGUMENTS", "slot_groups[].pattern must be linear or explicit.");
                }
                plan.SlotGroups.Add(group);
            }

            object propertiesRaw = Json.At(args, "properties");
            if (propertiesRaw != null)
            {
                var value = propertiesRaw as Dictionary<string, object>;
                if (value == null) throw new Fault("INVALID_ARGUMENTS", "properties must be an object.");
                ExactKeys(value, "properties", "designation", "name");
                plan.Properties = new NewPartProperties {
                    Designation = SafeTextAt(value, "designation"),
                    Name = SafeTextAt(value, "name")
                };
                if (plan.Properties.Designation == null && plan.Properties.Name == null)
                    throw new Fault("INVALID_ARGUMENTS", "properties must contain designation or name.");
            }

            object materialRaw = Json.At(args, "material");
            if (materialRaw != null)
            {
                string material = materialRaw as string;
                if (material != "AISI 304") throw new Fault("INVALID_ARGUMENTS", "Only the verified material AISI 304 is supported.");
                plan.MaterialName = material;
            }

            double holesVolumeMm3 = 0.0;
            foreach (ProfileHole hole in plan.Holes)
                holesVolumeMm3 += Math.PI * hole.Radius * hole.Radius * plan.ThicknessMm * hole.WallCount;
            double slotsVolumeMm3 = 0.0;
            foreach (ProfileSlot slot in plan.Slots)
                slotsVolumeMm3 += slot.AreaMm2 * plan.ThicknessMm * slot.WallCount;
            double rawVolumeMm3 = plan.CrossSectionAreaMm2 * plan.LengthMm;
            double netVolumeMm3 = rawVolumeMm3 - holesVolumeMm3 - slotsVolumeMm3;
            if (netVolumeMm3 <= 1.0) throw new Fault("INVALID_ARGUMENTS", "Cuts remove essentially the entire profile volume.");
            plan.ExpectedVolumeM3 = netVolumeMm3 * 1e-9;
            return plan;
        }

        internal double[][] CrossSectionPolygonYZ()
        {
            if (!IsEqualAngle) throw new InvalidOperationException("CrossSectionPolygonYZ is only valid for equal_angle.");
            return new[] {
                new[] { 0.0, 0.0 },
                new[] { LegAMm, 0.0 },
                new[] { LegAMm, ThicknessMm },
                new[] { ThicknessMm, ThicknessMm },
                new[] { ThicknessMm, LegBMm },
                new[] { 0.0, LegBMm }
            };
        }

        object CrossSectionJson()
        {
            if (IsEqualAngle)
                return Json.Obj("type", CrossSectionType, "leg_a_mm", LegAMm,
                    "leg_b_mm", LegBMm, "thickness_mm", ThicknessMm);
            if (IsRectangularTube)
                return Json.Obj("type", CrossSectionType, "width_mm", WidthMm,
                    "height_mm", HeightMm, "wall_thickness_mm", ThicknessMm,
                    "outer_corner_radius_mm", OuterCornerRadiusMm,
                    "inner_corner_radius_mm", InnerCornerRadiusMm);
            return Json.Obj("type", CrossSectionType, "outer_diameter_mm", OuterDiameterMm,
                "inner_diameter_mm", InnerDiameterMm, "wall_thickness_mm", ThicknessMm);
        }

        internal object ToJson()
        {
            var groups = new List<object>();
            foreach (ProfileHoleGroup group in Groups) groups.Add(group.ToJson());
            var slotGroups = new List<object>();
            foreach (ProfileSlotGroup group in SlotGroups) slotGroups.Add(group.ToJson());
            return Json.Obj("plan_version", PlanVersion,
                "cross_section", CrossSectionJson(),
                "length_mm", LengthMm, "hole_groups", groups.ToArray(),
                "slot_groups", slotGroups.ToArray(),
                "properties", Properties == null ? null : Properties.ToJson(), "material", MaterialName,
                "calculated", Json.Obj("cross_section_area_mm2", CrossSectionAreaMm2,
                    "hole_count", Holes.Count, "slot_count", Slots.Count,
                    "cut_wall_count", TotalCutWallCount(),
                    "net_volume_m3", ExpectedVolumeM3,
                    "envelope_xyz_mm", new[] { LengthMm, EnvelopeWidthMm, EnvelopeHeightMm }));
        }

        int TotalCutWallCount()
        {
            int result = 0;
            foreach (ProfileHole hole in Holes) result += hole.WallCount;
            foreach (ProfileSlot slot in Slots) result += slot.WallCount;
            return result;
        }
    }
}
