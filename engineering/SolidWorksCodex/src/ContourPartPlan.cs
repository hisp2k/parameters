using System;
using System.Collections.Generic;
using System.Globalization;

namespace SolidWorksLocal
{
    internal sealed class ContourPoint
    {
        internal double X, Y;
        internal ContourPoint(double x, double y) { X = x; Y = y; }
        internal object ToJson() { return Json.Obj("x_mm", X, "y_mm", Y); }
    }

    internal sealed class ContourSegment
    {
        internal string Type;
        internal ContourPoint Start, End, Center;
        internal bool Clockwise;
        internal double RadiusMm, SweepRadians;

        internal object ToJson()
        {
            if (Type == "line")
                return Json.Obj("type", Type, "start_x_mm", Start.X, "start_y_mm", Start.Y,
                    "end_x_mm", End.X, "end_y_mm", End.Y);
            return Json.Obj("type", Type, "start_x_mm", Start.X, "start_y_mm", Start.Y,
                "end_x_mm", End.X, "end_y_mm", End.Y, "center_x_mm", Center.X,
                "center_y_mm", Center.Y, "clockwise", Clockwise);
        }

        internal double SignedAreaContribution()
        {
            if (Type == "line") return 0.5 * (Start.X * End.Y - End.X * Start.Y);
            return 0.5 * (Center.X * (End.Y - Start.Y) - Center.Y * (End.X - Start.X) +
                RadiusMm * RadiusMm * SweepRadians);
        }

        internal void AppendFlattened(List<ContourPoint> points)
        {
            if (points.Count == 0) points.Add(new ContourPoint(Start.X, Start.Y));
            if (Type == "line") { points.Add(new ContourPoint(End.X, End.Y)); return; }
            double start = Math.Atan2(Start.Y - Center.Y, Start.X - Center.X);
            int steps = Math.Max(2, (int)Math.Ceiling(Math.Abs(SweepRadians) / (Math.PI / 90.0)));
            for (int i = 1; i <= steps; i++)
            {
                double angle = start + SweepRadians * i / steps;
                points.Add(new ContourPoint(Center.X + RadiusMm * Math.Cos(angle),
                    Center.Y + RadiusMm * Math.Sin(angle)));
            }
        }
    }

    internal sealed class ContourLoop
    {
        internal readonly List<ContourSegment> Segments = new List<ContourSegment>();
        internal readonly List<ContourPoint> Flattened = new List<ContourPoint>();
        internal double AreaMm2, MinX, MinY, MaxX, MaxY;
        internal object ToJson()
        {
            var rows = new List<object>();
            foreach (ContourSegment segment in Segments) rows.Add(segment.ToJson());
            return Json.Obj("segments", rows.ToArray(), "calculated_area_mm2", AreaMm2);
        }
    }

    internal sealed class LinearHolePattern
    {
        internal double StartX, StartY, StepX, StepY, Diameter;
        internal int Count;
        internal object ToJson()
        {
            return Json.Obj("start_x_mm", StartX, "start_y_mm", StartY,
                "step_x_mm", StepX, "step_y_mm", StepY, "count", Count,
                "diameter_mm", Diameter);
        }
    }

    // Strict numeric language for flat laser-cut parts. It models topology as
    // ordered closed loops; it never accepts code, paths, feature names or COM calls.
    internal sealed class ContourPartPlan
    {
        internal const string CurrentVersion = "1";
        internal const double JoinToleranceMm = 0.001;
        internal const double ClearanceMm = 0.05;
        internal string PlanVersion, MaterialName;
        internal double ThicknessMm, OuterAreaMm2, CutoutAreaMm2, NetAreaMm2,
            ExpectedVolumeM3, SpanXMm, SpanYMm;
        internal ContourLoop Outer;
        internal readonly List<ContourLoop> Inner = new List<ContourLoop>();
        internal readonly List<PlanHole> Holes = new List<PlanHole>();
        internal readonly List<LinearHolePattern> Patterns = new List<LinearHolePattern>();
        internal NewPartProperties Properties;

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
        static int IntegerAt(Dictionary<string, object> values, string key, int min, int max)
        {
            double number = NumberAt(values, key, min, max);
            if (number != Math.Truncate(number)) throw new Fault("INVALID_ARGUMENTS", key + " must be an integer.");
            return (int)number;
        }
        static bool BoolAt(Dictionary<string, object> value, string key)
        {
            object raw = Json.At(value, key);
            if (!(raw is bool)) throw new Fault("INVALID_ARGUMENTS", "Missing or invalid boolean: " + key);
            return (bool)raw;
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
        static double Distance(ContourPoint a, ContourPoint b)
        { double dx = a.X - b.X, dy = a.Y - b.Y; return Math.Sqrt(dx * dx + dy * dy); }
        static double Cross(ContourPoint a, ContourPoint b, ContourPoint c)
        { return (b.X - a.X) * (c.Y - a.Y) - (b.Y - a.Y) * (c.X - a.X); }
        static bool Between(double a, double b, double value)
        { return value >= Math.Min(a, b) - 1e-7 && value <= Math.Max(a, b) + 1e-7; }
        static bool OnSegment(ContourPoint a, ContourPoint b, ContourPoint p)
        { return Math.Abs(Cross(a, b, p)) <= 1e-7 && Between(a.X, b.X, p.X) && Between(a.Y, b.Y, p.Y); }
        static int Side(double value) { return value > 1e-7 ? 1 : value < -1e-7 ? -1 : 0; }
        static bool Intersects(ContourPoint a, ContourPoint b, ContourPoint c, ContourPoint d)
        {
            int abC = Side(Cross(a, b, c)), abD = Side(Cross(a, b, d));
            int cdA = Side(Cross(c, d, a)), cdB = Side(Cross(c, d, b));
            if (abC == 0 && OnSegment(a, b, c)) return true;
            if (abD == 0 && OnSegment(a, b, d)) return true;
            if (cdA == 0 && OnSegment(c, d, a)) return true;
            if (cdB == 0 && OnSegment(c, d, b)) return true;
            return abC != abD && cdA != cdB;
        }
        static double DistanceToSegment(ContourPoint p, ContourPoint a, ContourPoint b)
        {
            double dx = b.X - a.X, dy = b.Y - a.Y;
            double length2 = dx * dx + dy * dy;
            if (length2 <= 1e-12) return Distance(p, a);
            double t = ((p.X - a.X) * dx + (p.Y - a.Y) * dy) / length2;
            t = Math.Max(0, Math.Min(1, t));
            return Distance(p, new ContourPoint(a.X + t * dx, a.Y + t * dy));
        }
        static bool PointInside(ContourPoint p, IList<ContourPoint> polygon)
        {
            bool inside = false;
            for (int i = 0, j = polygon.Count - 1; i < polygon.Count; j = i++)
            {
                ContourPoint a = polygon[i], b = polygon[j];
                if (((a.Y > p.Y) != (b.Y > p.Y)) &&
                    p.X < (b.X - a.X) * (p.Y - a.Y) / (b.Y - a.Y) + a.X) inside = !inside;
            }
            return inside;
        }
        static double BoundaryDistance(ContourPoint p, IList<ContourPoint> polygon)
        {
            double result = double.MaxValue;
            for (int i = 0; i < polygon.Count; i++)
                result = Math.Min(result, DistanceToSegment(p, polygon[i], polygon[(i + 1) % polygon.Count]));
            return result;
        }
        static bool LoopsIntersect(IList<ContourPoint> a, IList<ContourPoint> b)
        {
            for (int i = 0; i < a.Count; i++)
                for (int j = 0; j < b.Count; j++)
                    if (Intersects(a[i], a[(i + 1) % a.Count], b[j], b[(j + 1) % b.Count])) return true;
            return false;
        }
        static void ValidateSimple(IList<ContourPoint> points, string label)
        {
            if (points.Count < 3) throw new Fault("INVALID_ARGUMENTS", label + " is degenerate.");
            for (int i = 0; i < points.Count; i++)
            {
                if (Distance(points[i], points[(i + 1) % points.Count]) < 0.0001)
                    throw new Fault("INVALID_ARGUMENTS", label + " contains a duplicate edge.");
                for (int j = i + 1; j < points.Count; j++)
                {
                    if (j == i + 1 || (i == 0 && j == points.Count - 1)) continue;
                    if (Intersects(points[i], points[(i + 1) % points.Count],
                        points[j], points[(j + 1) % points.Count]))
                        throw new Fault("INVALID_ARGUMENTS", label + " intersects itself.");
                }
            }
        }
        static ContourLoop ParseLoop(Dictionary<string, object> value, string label)
        {
            ExactKeys(value, label, "segments");
            Array rawSegments = ArrayAt(value, "segments", true);
            if (rawSegments.Length < 2 || rawSegments.Length > 256)
                throw new Fault("INVALID_ARGUMENTS", label + " requires 2 to 256 ordered segments.");
            var loop = new ContourLoop();
            double signedArea = 0.0;
            foreach (object raw in rawSegments)
            {
                var item = raw as Dictionary<string, object>;
                if (item == null) throw new Fault("INVALID_ARGUMENTS", "Every " + label + " segment must be an object.");
                string type = StringAt(item, "type").ToLowerInvariant();
                if (type != "line" && type != "arc")
                    throw new Fault("INVALID_ARGUMENTS", "Contour segment type must be line or arc.");
                if (type == "line")
                    ExactKeys(item, "line segment", "type", "start_x_mm", "start_y_mm", "end_x_mm", "end_y_mm");
                else
                    ExactKeys(item, "arc segment", "type", "start_x_mm", "start_y_mm", "end_x_mm", "end_y_mm",
                        "center_x_mm", "center_y_mm", "clockwise");
                var segment = new ContourSegment {
                    Type = type,
                    Start = new ContourPoint(NumberAt(item, "start_x_mm", -10000, 10000), NumberAt(item, "start_y_mm", -10000, 10000)),
                    End = new ContourPoint(NumberAt(item, "end_x_mm", -10000, 10000), NumberAt(item, "end_y_mm", -10000, 10000))
                };
                if (Distance(segment.Start, segment.End) < 0.001)
                    throw new Fault("INVALID_ARGUMENTS", "Every contour segment needs distinct start and end points.");
                if (type == "arc")
                {
                    segment.Center = new ContourPoint(NumberAt(item, "center_x_mm", -10000, 10000), NumberAt(item, "center_y_mm", -10000, 10000));
                    segment.Clockwise = BoolAt(item, "clockwise");
                    double r1 = Distance(segment.Center, segment.Start), r2 = Distance(segment.Center, segment.End);
                    if (r1 < 0.1 || Math.Abs(r1 - r2) > Math.Max(0.001, r1 * 1e-6))
                        throw new Fault("INVALID_ARGUMENTS", "Arc start and end must have the same radius from the supplied centre.");
                    segment.RadiusMm = (r1 + r2) / 2.0;
                    double a0 = Math.Atan2(segment.Start.Y - segment.Center.Y, segment.Start.X - segment.Center.X);
                    double a1 = Math.Atan2(segment.End.Y - segment.Center.Y, segment.End.X - segment.Center.X);
                    double sweep = a1 - a0;
                    if (segment.Clockwise) { while (sweep >= 0) sweep -= 2.0 * Math.PI; }
                    else { while (sweep <= 0) sweep += 2.0 * Math.PI; }
                    if (Math.Abs(sweep) >= 2.0 * Math.PI - 1e-8)
                        throw new Fault("INVALID_ARGUMENTS", "Use at least two arcs for a complete circle.");
                    segment.SweepRadians = sweep;
                }
                if (loop.Segments.Count > 0 && Distance(loop.Segments[loop.Segments.Count - 1].End, segment.Start) > JoinToleranceMm)
                    throw new Fault("INVALID_ARGUMENTS", label + " segments are not connected in order within 0.001 mm.");
                loop.Segments.Add(segment);
                signedArea += segment.SignedAreaContribution();
                segment.AppendFlattened(loop.Flattened);
            }
            if (Distance(loop.Segments[loop.Segments.Count - 1].End, loop.Segments[0].Start) > JoinToleranceMm)
                throw new Fault("INVALID_ARGUMENTS", label + " is not closed within 0.001 mm.");
            if (loop.Flattened.Count > 1 && Distance(loop.Flattened[0], loop.Flattened[loop.Flattened.Count - 1]) <= JoinToleranceMm)
                loop.Flattened.RemoveAt(loop.Flattened.Count - 1);
            ValidateSimple(loop.Flattened, label);
            loop.AreaMm2 = Math.Abs(signedArea);
            if (loop.AreaMm2 < 1.0) throw new Fault("INVALID_ARGUMENTS", label + " area is too small.");
            loop.MinX = loop.MinY = double.MaxValue; loop.MaxX = loop.MaxY = double.MinValue;
            foreach (ContourPoint p in loop.Flattened)
            {
                loop.MinX = Math.Min(loop.MinX, p.X); loop.MinY = Math.Min(loop.MinY, p.Y);
                loop.MaxX = Math.Max(loop.MaxX, p.X); loop.MaxY = Math.Max(loop.MaxY, p.Y);
            }
            return loop;
        }
        void AddHole(PlanHole hole)
        {
            if (Holes.Count >= 256) throw new Fault("INVALID_ARGUMENTS", "At most 256 circular holes are allowed.");
            var center = new ContourPoint(hole.X, hole.Y);
            double required = hole.Radius + ClearanceMm;
            if (!PointInside(center, Outer.Flattened) || BoundaryDistance(center, Outer.Flattened) < required)
                throw new Fault("INVALID_ARGUMENTS", "Every hole must remain inside the outer contour with at least 0.05 mm clearance.");
            foreach (ContourLoop inner in Inner)
                if (PointInside(center, inner.Flattened) || BoundaryDistance(center, inner.Flattened) < required)
                    throw new Fault("INVALID_ARGUMENTS", "A circular hole overlaps or touches an inner cutout.");
            foreach (PlanHole existing in Holes)
                if (Math.Sqrt((existing.X - hole.X) * (existing.X - hole.X) + (existing.Y - hole.Y) * (existing.Y - hole.Y)) <
                    existing.Radius + hole.Radius + ClearanceMm)
                    throw new Fault("INVALID_ARGUMENTS", "Circular holes overlap or touch.");
            Holes.Add(hole);
        }

        internal static ContourPartPlan Parse(Dictionary<string, object> args)
        {
            if (args == null) throw new Fault("INVALID_ARGUMENTS", "arguments must be an object.");
            ExactKeys(args, "sheet contour plan", "plan_version", "thickness_mm", "outer_contour", "inner_contours",
                "holes", "linear_hole_patterns", "properties", "material");
            var plan = new ContourPartPlan { PlanVersion = StringAt(args, "plan_version") };
            if (plan.PlanVersion != CurrentVersion)
                throw new Fault("INVALID_ARGUMENTS", "Unsupported sheet-contour plan version. Use plan_version=1.");
            plan.ThicknessMm = NumberAt(args, "thickness_mm", 0.2, 500.0);
            plan.Outer = ParseLoop(ObjectAt(args, "outer_contour"), "outer contour");
            plan.OuterAreaMm2 = plan.Outer.AreaMm2;
            plan.SpanXMm = plan.Outer.MaxX - plan.Outer.MinX;
            plan.SpanYMm = plan.Outer.MaxY - plan.Outer.MinY;
            if (plan.SpanXMm < 1 || plan.SpanYMm < 1 || plan.SpanXMm > 10000 || plan.SpanYMm > 10000)
                throw new Fault("INVALID_ARGUMENTS", "Outer contour envelope must be between 1 and 10000 mm on each axis.");

            Array rawInner = ArrayAt(args, "inner_contours", false);
            if (rawInner.Length > 32) throw new Fault("INVALID_ARGUMENTS", "At most 32 inner contours are allowed.");
            foreach (object raw in rawInner)
            {
                var value = raw as Dictionary<string, object>;
                if (value == null) throw new Fault("INVALID_ARGUMENTS", "Each inner contour must be an object.");
                ContourLoop inner = ParseLoop(value, "inner contour");
                foreach (ContourPoint p in inner.Flattened)
                    if (!PointInside(p, plan.Outer.Flattened) || BoundaryDistance(p, plan.Outer.Flattened) < ClearanceMm)
                        throw new Fault("INVALID_ARGUMENTS", "Every inner contour must remain inside the outer contour with 0.05 mm clearance.");
                if (LoopsIntersect(plan.Outer.Flattened, inner.Flattened))
                    throw new Fault("INVALID_ARGUMENTS", "An inner contour intersects the outer contour.");
                foreach (ContourLoop existing in plan.Inner)
                    if (LoopsIntersect(existing.Flattened, inner.Flattened) || PointInside(inner.Flattened[0], existing.Flattened) || PointInside(existing.Flattened[0], inner.Flattened))
                        throw new Fault("INVALID_ARGUMENTS", "Inner contours overlap, intersect or contain each other.");
                plan.Inner.Add(inner); plan.CutoutAreaMm2 += inner.AreaMm2;
            }

            Array rawHoles = ArrayAt(args, "holes", false);
            foreach (object raw in rawHoles)
            {
                var value = raw as Dictionary<string, object>;
                if (value == null) throw new Fault("INVALID_ARGUMENTS", "Each hole must be an object.");
                ExactKeys(value, "hole", "x_mm", "y_mm", "diameter_mm");
                plan.AddHole(new PlanHole(NumberAt(value, "x_mm", -10000, 10000),
                    NumberAt(value, "y_mm", -10000, 10000), NumberAt(value, "diameter_mm", 0.2, 2000)));
            }

            Array rawPatterns = ArrayAt(args, "linear_hole_patterns", false);
            if (rawPatterns.Length > 16) throw new Fault("INVALID_ARGUMENTS", "At most 16 linear hole patterns are allowed.");
            foreach (object raw in rawPatterns)
            {
                var value = raw as Dictionary<string, object>;
                if (value == null) throw new Fault("INVALID_ARGUMENTS", "Each linear hole pattern must be an object.");
                ExactKeys(value, "linear hole pattern", "start_x_mm", "start_y_mm", "step_x_mm", "step_y_mm", "count", "diameter_mm");
                var pattern = new LinearHolePattern {
                    StartX = NumberAt(value, "start_x_mm", -10000, 10000),
                    StartY = NumberAt(value, "start_y_mm", -10000, 10000),
                    StepX = NumberAt(value, "step_x_mm", -10000, 10000),
                    StepY = NumberAt(value, "step_y_mm", -10000, 10000),
                    Count = IntegerAt(value, "count", 2, 256),
                    Diameter = NumberAt(value, "diameter_mm", 0.2, 2000)
                };
                if (Math.Sqrt(pattern.StepX * pattern.StepX + pattern.StepY * pattern.StepY) < pattern.Diameter + ClearanceMm)
                    throw new Fault("INVALID_ARGUMENTS", "Linear hole-pattern pitch must exceed the hole diameter by 0.05 mm.");
                if (plan.Holes.Count + pattern.Count > 256)
                    throw new Fault("INVALID_ARGUMENTS", "Explicit and patterned holes exceed the 256-hole limit.");
                for (int i = 0; i < pattern.Count; i++)
                    plan.AddHole(new PlanHole(pattern.StartX + i * pattern.StepX,
                        pattern.StartY + i * pattern.StepY, pattern.Diameter));
                plan.Patterns.Add(pattern);
            }

            object propertiesRaw = Json.At(args, "properties");
            if (propertiesRaw != null)
            {
                var value = propertiesRaw as Dictionary<string, object>;
                if (value == null) throw new Fault("INVALID_ARGUMENTS", "properties must be an object.");
                ExactKeys(value, "properties", "designation", "name");
                plan.Properties = new NewPartProperties { Designation = SafeTextAt(value, "designation"), Name = SafeTextAt(value, "name") };
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

            double holesArea = 0.0;
            foreach (PlanHole hole in plan.Holes) holesArea += Math.PI * hole.Radius * hole.Radius;
            plan.NetAreaMm2 = plan.OuterAreaMm2 - plan.CutoutAreaMm2 - holesArea;
            if (plan.NetAreaMm2 <= 1.0) throw new Fault("INVALID_ARGUMENTS", "Cutouts and holes remove the entire sheet contour.");
            plan.ExpectedVolumeM3 = plan.NetAreaMm2 * plan.ThicknessMm * 1e-9;
            return plan;
        }

        internal object ToJson()
        {
            var inner = new List<object>(); foreach (ContourLoop loop in Inner) inner.Add(loop.ToJson());
            var holes = new List<object>(); foreach (PlanHole hole in Holes) holes.Add(hole.ToJson());
            var patterns = new List<object>(); foreach (LinearHolePattern pattern in Patterns) patterns.Add(pattern.ToJson());
            return Json.Obj("plan_version", PlanVersion, "thickness_mm", ThicknessMm,
                "outer_contour", Outer.ToJson(), "inner_contours", inner.ToArray(),
                "holes", holes.ToArray(), "linear_hole_patterns", patterns.ToArray(),
                "properties", Properties == null ? null : Properties.ToJson(), "material", MaterialName,
                "calculated", Json.Obj("outer_area_mm2", OuterAreaMm2, "inner_cutout_area_mm2", CutoutAreaMm2,
                    "net_area_mm2", NetAreaMm2, "net_volume_m3", ExpectedVolumeM3,
                    "envelope_xyz_mm", new[] { SpanXMm, SpanYMm, ThicknessMm }));
        }
    }
}
