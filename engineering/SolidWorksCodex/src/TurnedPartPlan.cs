using System;
using System.Collections.Generic;
using System.Globalization;

namespace SolidWorksLocal
{
    internal sealed class TurnedProfilePoint
    {
        internal double X, Diameter;
        internal double Radius { get { return Diameter / 2.0; } }
        internal TurnedProfilePoint(double x, double diameter) { X = x; Diameter = diameter; }
        internal object ToJson() { return Json.Obj("x_mm", X, "diameter_mm", Diameter); }
    }

    internal sealed class RadialHole
    {
        internal double X, Diameter;
        internal double Radius { get { return Diameter / 2.0; } }
        internal RadialHole(double x, double diameter) { X = x; Diameter = diameter; }
        internal object ToJson() { return Json.Obj("x_mm", X, "diameter_mm", Diameter); }
    }

    internal sealed class SideFlatSlot
    {
        internal double StartX, EndX, FloorRadius;
        internal string Side;
        internal SideFlatSlot(double startX, double endX, double floorRadius, string side)
        { StartX = startX; EndX = endX; FloorRadius = floorRadius; Side = side; }
        internal object ToJson()
        {
            return Json.Obj("x_start_mm", StartX, "x_end_mm", EndX,
                "floor_radius_mm", FloorRadius, "side", Side);
        }
    }

    internal sealed class LongitudinalSplineZone
    {
        internal double StartX, TipEndX, EndX, RootDiameter, TipDiameter, ToothWidth, PhaseDegrees;
        internal int ToothCount;
        internal double RootRadius { get { return RootDiameter / 2.0; } }
        internal double TipRadius { get { return TipDiameter / 2.0; } }
        internal double MidX { get { return (StartX + EndX) / 2.0; } }
        internal object ToJson()
        {
            return Json.Obj("start_x_mm", StartX, "tip_end_x_mm", TipEndX, "end_x_mm", EndX,
                "root_diameter_mm", RootDiameter, "tip_diameter_mm", TipDiameter,
                "tooth_count", ToothCount, "tooth_width_mm", ToothWidth,
                "phase_angle_deg", PhaseDegrees);
        }
    }

    internal sealed class NewPartProperties
    {
        internal string Designation, Name;
        internal object ToJson() { return Json.Obj("designation", Designation, "name", Name); }
    }

    // Strict plan language for a single turned part. Coordinates are the axial
    // X position and full diameter in millimetres. Only numeric geometry is
    // accepted: no paths, names, code, macros or arbitrary COM members.
    internal sealed class TurnedPartPlan
    {
        internal const string BasicVersion = "2";
        internal const string CurrentVersion = "3";
        internal const double ClearanceMm = 0.05;
        internal const double ReferenceTolerance = 0.0005; // 0.05%
        internal readonly List<TurnedProfilePoint> Outer = new List<TurnedProfilePoint>();
        internal readonly List<TurnedProfilePoint> Bore = new List<TurnedProfilePoint>();
        internal readonly List<RadialHole> RadialHoles = new List<RadialHole>();
        internal readonly List<SideFlatSlot> SideSlots = new List<SideFlatSlot>();
        internal string PlanVersion;
        internal LongitudinalSplineZone Spline;
        internal NewPartProperties Properties;
        internal double LengthMm, MaximumDiameterMm, AxisymmetricVolumeM3;
        internal double? ReferenceVolumeM3;

        static void ExactKeys(Dictionary<string, object> value, string label, params string[] allowedNames)
        {
            var allowed = new HashSet<string>(allowedNames, StringComparer.Ordinal);
            foreach (string key in value.Keys)
                if (!allowed.Contains(key)) throw new Fault("INVALID_ARGUMENTS", label + " contains an unexpected field: " + key);
        }
        static Array ArrayAt(Dictionary<string, object> value, string key, bool required)
        {
            object raw = Json.At(value, key);
            if (raw == null && !required) return new object[0];
            var result = raw as Array;
            if (result == null) throw new Fault("INVALID_ARGUMENTS", key + " must be an array.");
            return result;
        }
        static string StringAt(Dictionary<string, object> value, string key)
        {
            string result = Json.At(value, key) as string;
            if (string.IsNullOrWhiteSpace(result)) throw new Fault("INVALID_ARGUMENTS", "Missing or invalid string: " + key);
            return result;
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
        static int IntegerAt(Dictionary<string, object> value, string key, int min, int max)
        {
            object raw = Json.At(value, key);
            if (!(raw is int || raw is long || raw is decimal || raw is double))
                throw new Fault("INVALID_ARGUMENTS", "Missing or invalid integer: " + key);
            double number = Convert.ToDouble(raw, CultureInfo.InvariantCulture);
            if (double.IsNaN(number) || double.IsInfinity(number) || number != Math.Truncate(number) ||
                number < min || number > max)
                throw new Fault("INVALID_ARGUMENTS", key + " is out of range.");
            return (int)number;
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
        static List<TurnedProfilePoint> Profile(Array raw, string label, int minimum, bool allowZeroDiameter)
        {
            if (raw.Length < minimum || raw.Length > 40)
                throw new Fault("INVALID_ARGUMENTS", label + " requires " + minimum + " to 40 points.");
            var result = new List<TurnedProfilePoint>();
            double previousX = -1.0;
            foreach (object item in raw)
            {
                var point = item as Dictionary<string, object>;
                if (point == null) throw new Fault("INVALID_ARGUMENTS", "Each " + label + " point must be an object.");
                ExactKeys(point, label + " point", "x_mm", "diameter_mm");
                double x = NumberAt(point, "x_mm", 0.0, 2000.0);
                double diameter = NumberAt(point, "diameter_mm", allowZeroDiameter ? 0.0 : 1.0, 2000.0);
                if (result.Count > 0 && x < previousX - 1e-9)
                    throw new Fault("INVALID_ARGUMENTS", label + " x_mm values must be nondecreasing.");
                if (result.Count > 0)
                {
                    TurnedProfilePoint p = result[result.Count - 1];
                    if (Math.Abs(x - p.X) < 1e-9 && Math.Abs(diameter - p.Diameter) < 1e-9)
                        throw new Fault("INVALID_ARGUMENTS", label + " contains duplicate consecutive points.");
                }
                result.Add(new TurnedProfilePoint(x, diameter));
                previousX = x;
            }
            return result;
        }
        static double RevolvedVolumeMm3(List<TurnedProfilePoint> points)
        {
            double integral = 0.0;
            for (int i = 1; i < points.Count; i++)
            {
                double dx = points[i].X - points[i - 1].X;
                double r0 = points[i - 1].Radius, r1 = points[i].Radius;
                integral += dx * (r0 * r0 + r0 * r1 + r1 * r1) / 3.0;
            }
            return Math.PI * integral;
        }
        double MinimumOuterRadius(double startX, double endX)
        {
            double minimum = double.MaxValue;
            for (int i = 0; i < Outer.Count; i++)
                if (Outer[i].X >= startX - 1e-9 && Outer[i].X <= endX + 1e-9)
                    minimum = Math.Min(minimum, Outer[i].Radius);
            for (int i = 1; i < Outer.Count; i++)
            {
                TurnedProfilePoint a = Outer[i - 1], b = Outer[i];
                if (b.X < startX || a.X > endX) continue;
                minimum = Math.Min(minimum, Math.Min(a.Radius, b.Radius));
            }
            return minimum;
        }
        double OuterRadiusAt(double x)
        {
            double result = double.MaxValue;
            for (int i = 1; i < Outer.Count; i++)
            {
                TurnedProfilePoint a = Outer[i - 1], b = Outer[i];
                if (x < a.X - 1e-9 || x > b.X + 1e-9) continue;
                double radius;
                if (Math.Abs(b.X - a.X) < 1e-9) radius = Math.Min(a.Radius, b.Radius);
                else
                {
                    double t = (x - a.X) / (b.X - a.X);
                    radius = a.Radius + t * (b.Radius - a.Radius);
                }
                result = Math.Min(result, radius);
            }
            return result;
        }

        internal static TurnedPartPlan Parse(Dictionary<string, object> args)
        {
            if (args == null) throw new Fault("INVALID_ARGUMENTS", "arguments must be an object.");
            ExactKeys(args, "turned plan", "plan_version", "outer_profile", "axial_bore_profile",
                "radial_holes", "side_flat_slots", "spline_zone", "properties", "reference_volume_mm3");
            string version = StringAt(args, "plan_version");
            if (version != BasicVersion && version != CurrentVersion)
                throw new Fault("INVALID_ARGUMENTS", "Unsupported turned plan version. Use plan_version=2 or 3.");

            var plan = new TurnedPartPlan();
            plan.PlanVersion = version;
            plan.Outer.AddRange(Profile(ArrayAt(args, "outer_profile", true), "outer_profile", 2, false));
            if (Math.Abs(plan.Outer[0].X) > 1e-9)
                throw new Fault("INVALID_ARGUMENTS", "outer_profile must start at x_mm=0.");
            plan.LengthMm = plan.Outer[plan.Outer.Count - 1].X;
            if (plan.LengthMm < 5.0)
                throw new Fault("INVALID_ARGUMENTS", "The turned part must be at least 5 mm long.");
            foreach (TurnedProfilePoint point in plan.Outer)
                plan.MaximumDiameterMm = Math.Max(plan.MaximumDiameterMm, point.Diameter);

            Array boreRaw = ArrayAt(args, "axial_bore_profile", false);
            if (boreRaw.Length > 0)
            {
                plan.Bore.AddRange(Profile(boreRaw, "axial_bore_profile", 2, true));
                TurnedProfilePoint first = plan.Bore[0], last = plan.Bore[plan.Bore.Count - 1];
                if (first.X < 0.5 || first.X >= plan.LengthMm - 0.5 || Math.Abs(first.Diameter) > 1e-9)
                    throw new Fault("INVALID_ARGUMENTS", "The supported axial bore must be blind: begin inside the part with diameter_mm=0.");
                if (Math.Abs(last.X - plan.LengthMm) > 1e-6 || last.Diameter < 1.0)
                    throw new Fault("INVALID_ARGUMENTS", "axial_bore_profile must end open at the final outer-profile x_mm.");
                double maxBoreRadius = 0.0;
                foreach (TurnedProfilePoint point in plan.Bore) maxBoreRadius = Math.Max(maxBoreRadius, point.Radius);
                if (maxBoreRadius + ClearanceMm >= plan.MinimumOuterRadius(first.X, plan.LengthMm))
                    throw new Fault("INVALID_ARGUMENTS", "The axial bore must remain inside the smallest surrounding outer radius.");
            }

            Array holeRaw = ArrayAt(args, "radial_holes", false);
            if (holeRaw.Length > 16) throw new Fault("INVALID_ARGUMENTS", "At most 16 radial holes are allowed.");
            foreach (object item in holeRaw)
            {
                var hole = item as Dictionary<string, object>;
                if (hole == null) throw new Fault("INVALID_ARGUMENTS", "Each radial hole must be an object.");
                ExactKeys(hole, "radial hole", "x_mm", "diameter_mm");
                var parsed = new RadialHole(NumberAt(hole, "x_mm", 0.5, plan.LengthMm - 0.5),
                    NumberAt(hole, "diameter_mm", 1.0, 200.0));
                double outer = plan.OuterRadiusAt(parsed.X);
                if (outer == double.MaxValue || parsed.Radius + ClearanceMm >= outer)
                    throw new Fault("INVALID_ARGUMENTS", "Each radial hole must fit inside the local outer diameter.");
                foreach (RadialHole existing in plan.RadialHoles)
                    if (Math.Abs(existing.X - parsed.X) < existing.Radius + parsed.Radius + ClearanceMm)
                        throw new Fault("INVALID_ARGUMENTS", "Parallel radial holes overlap or touch each other.");
                plan.RadialHoles.Add(parsed);
            }

            Array slotRaw = ArrayAt(args, "side_flat_slots", false);
            if (slotRaw.Length > 8) throw new Fault("INVALID_ARGUMENTS", "At most 8 side flat slots are allowed.");
            foreach (object item in slotRaw)
            {
                var slot = item as Dictionary<string, object>;
                if (slot == null) throw new Fault("INVALID_ARGUMENTS", "Each side flat slot must be an object.");
                ExactKeys(slot, "side flat slot", "x_start_mm", "x_end_mm", "floor_radius_mm", "side");
                double start = NumberAt(slot, "x_start_mm", 0.0, plan.LengthMm);
                double end = NumberAt(slot, "x_end_mm", 0.0, plan.LengthMm);
                double floor = NumberAt(slot, "floor_radius_mm", 0.0, plan.MaximumDiameterMm / 2.0);
                string side = StringAt(slot, "side").ToLowerInvariant();
                if (side != "positive" && side != "negative")
                    throw new Fault("INVALID_ARGUMENTS", "side must be positive or negative.");
                if (end - start < 0.5)
                    throw new Fault("INVALID_ARGUMENTS", "A side flat slot must be at least 0.5 mm wide.");
                if (floor + ClearanceMm >= plan.MinimumOuterRadius(start, end))
                    throw new Fault("INVALID_ARGUMENTS", "floor_radius_mm must cut into the outer profile.");
                plan.SideSlots.Add(new SideFlatSlot(start, end, floor, side));
            }

            object splineRaw = Json.At(args, "spline_zone");
            object propertiesRaw = Json.At(args, "properties");
            if (version == BasicVersion && (splineRaw != null || propertiesRaw != null))
                throw new Fault("INVALID_ARGUMENTS", "spline_zone and properties require plan_version=3.");
            if (version == CurrentVersion)
            {
                var spline = splineRaw as Dictionary<string, object>;
                if (spline == null) throw new Fault("INVALID_ARGUMENTS", "plan_version=3 requires spline_zone.");
                ExactKeys(spline, "spline_zone", "start_x_mm", "tip_end_x_mm", "end_x_mm",
                    "root_diameter_mm", "tip_diameter_mm", "tooth_count", "tooth_width_mm", "phase_angle_deg");
                var parsed = new LongitudinalSplineZone();
                parsed.StartX = NumberAt(spline, "start_x_mm", 0.5, plan.LengthMm - 1.0);
                parsed.TipEndX = NumberAt(spline, "tip_end_x_mm", 1.0, plan.LengthMm);
                parsed.EndX = NumberAt(spline, "end_x_mm", 1.0, plan.LengthMm);
                parsed.RootDiameter = NumberAt(spline, "root_diameter_mm", 2.0, 2000.0);
                parsed.TipDiameter = NumberAt(spline, "tip_diameter_mm", 2.0, 2000.0);
                parsed.ToothCount = IntegerAt(spline, "tooth_count", 2, 64);
                parsed.ToothWidth = NumberAt(spline, "tooth_width_mm", 0.5, 500.0);
                parsed.PhaseDegrees = NumberAt(spline, "phase_angle_deg", -360.0, 360.0);
                if (parsed.TipEndX - parsed.StartX < 1.0 || parsed.EndX < parsed.TipEndX ||
                    parsed.EndX - parsed.StartX < 2.0)
                    throw new Fault("INVALID_ARGUMENTS", "spline_zone axial positions are invalid.");
                if (parsed.TipDiameter <= parsed.RootDiameter + 0.1)
                    throw new Fault("INVALID_ARGUMENTS", "tip_diameter_mm must exceed root_diameter_mm.");
                double pitchHalf = Math.PI / parsed.ToothCount;
                if (parsed.ToothWidth / 2.0 + ClearanceMm >= parsed.RootRadius * Math.Sin(pitchHalf))
                    throw new Fault("INVALID_ARGUMENTS", "tooth_width_mm does not fit the requested tooth count at the root diameter.");
                double middleTipRadius = plan.OuterRadiusAt((parsed.StartX + parsed.TipEndX) / 2.0);
                double middleTaperX = (parsed.TipEndX + parsed.EndX) / 2.0;
                double expectedTaperRadius = parsed.EndX == parsed.TipEndX ? parsed.RootRadius :
                    (parsed.TipRadius + parsed.RootRadius) / 2.0;
                if (Math.Abs(middleTipRadius - parsed.TipRadius) > 0.05 ||
                    Math.Abs(plan.OuterRadiusAt(middleTaperX) - expectedTaperRadius) > 0.05 ||
                    Math.Abs(plan.OuterRadiusAt(parsed.EndX + Math.Min(0.1, (plan.LengthMm - parsed.EndX) / 2.0)) - parsed.RootRadius) > 0.05)
                    throw new Fault("INVALID_ARGUMENTS", "outer_profile must contain the requested spline tip cylinder, end taper and root diameter.");
                plan.Spline = parsed;

                if (propertiesRaw != null)
                {
                    var values = propertiesRaw as Dictionary<string, object>;
                    if (values == null) throw new Fault("INVALID_ARGUMENTS", "properties must be an object.");
                    ExactKeys(values, "properties", "designation", "name");
                    var props = new NewPartProperties {
                        Designation = SafeTextAt(values, "designation"), Name = SafeTextAt(values, "name") };
                    if (props.Designation == null && props.Name == null)
                        throw new Fault("INVALID_ARGUMENTS", "properties must contain designation or name.");
                    plan.Properties = props;
                }
            }

            double outerVolume = RevolvedVolumeMm3(plan.Outer);
            double boreVolume = plan.Bore.Count == 0 ? 0.0 : RevolvedVolumeMm3(plan.Bore);
            double axisymmetric = outerVolume - boreVolume;
            if (axisymmetric <= 1.0)
                throw new Fault("INVALID_ARGUMENTS", "The axial bore removes the entire revolved body.");
            plan.AxisymmetricVolumeM3 = axisymmetric * 1e-9;

            object referenceRaw = Json.At(args, "reference_volume_mm3");
            if (referenceRaw != null)
            {
                double reference = NumberAt(args, "reference_volume_mm3", 1.0, 1e12);
                if (reference > axisymmetric * 1.001)
                    throw new Fault("INVALID_ARGUMENTS", "reference_volume_mm3 cannot exceed the axisymmetric body volume.");
                plan.ReferenceVolumeM3 = reference * 1e-9;
            }
            return plan;
        }

        internal object ToJson()
        {
            var outer = new List<object>(); foreach (TurnedProfilePoint p in Outer) outer.Add(p.ToJson());
            var bore = new List<object>(); foreach (TurnedProfilePoint p in Bore) bore.Add(p.ToJson());
            var holes = new List<object>(); foreach (RadialHole h in RadialHoles) holes.Add(h.ToJson());
            var slots = new List<object>(); foreach (SideFlatSlot s in SideSlots) slots.Add(s.ToJson());
            return Json.Obj("plan_version", PlanVersion, "outer_profile", outer.ToArray(),
                "axial_bore_profile", bore.ToArray(), "radial_holes", holes.ToArray(),
                "side_flat_slots", slots.ToArray(),
                "spline_zone", Spline == null ? null : Spline.ToJson(),
                "properties", Properties == null ? null : Properties.ToJson(),
                "reference_volume_mm3", ReferenceVolumeM3.HasValue ? (object)(ReferenceVolumeM3.Value * 1e9) : null,
                "calculated", Json.Obj("length_mm", LengthMm, "maximum_diameter_mm", MaximumDiameterMm,
                    "axisymmetric_volume_m3", AxisymmetricVolumeM3,
                    "reference_tolerance_percent", ReferenceTolerance * 100.0));
        }
    }
}
