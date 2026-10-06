using System;
using System.Collections.Generic;
using System.Globalization;

namespace SolidWorksLocal
{
    internal sealed class PlanPoint
    {
        internal double X, Y;
        // Plan v6 only: optional convex-corner finishing applied at this vertex.
        internal string CornerStyle;
        internal double CornerSizeMm;
        internal double InteriorAngleRad;
        internal double TangentLengthMm;
        internal double CornerAreaRemovedMm2;
        internal double ArcCenterXMm, ArcCenterYMm;
        internal double TangentInXMm, TangentInYMm, TangentOutXMm, TangentOutYMm;
        internal PlanPoint(double x, double y) { X = x; Y = y; }
        internal object ToJson()
        {
            if (CornerStyle == null) return Json.Obj("x_mm", X, "y_mm", Y);
            return Json.Obj("x_mm", X, "y_mm", Y,
                "corner_style", CornerStyle, "corner_size_mm", CornerSizeMm);
        }
    }

    internal sealed class PlanHole
    {
        internal double X, Y, Diameter;
        internal double Radius { get { return Diameter / 2.0; } }
        internal PlanHole(double x, double y, double diameter) { X = x; Y = y; Diameter = diameter; }
        internal object ToJson() { return Json.Obj("x_mm", X, "y_mm", Y, "diameter_mm", Diameter); }
    }

    internal sealed class CircularHolePattern
    {
        internal double PitchCircleDiameter, HoleDiameter, StartAngleDegrees;
        internal int HoleCount;
        internal object ToJson()
        {
            return Json.Obj("pitch_circle_diameter_mm", PitchCircleDiameter,
                "hole_diameter_mm", HoleDiameter, "hole_count", HoleCount,
                "start_angle_deg", StartAngleDegrees);
        }
    }

    internal sealed class PlanBounds
    {
        internal double MinX, MinY, MaxX, MaxY;
        internal PlanBounds(double minX, double minY, double maxX, double maxY)
        { MinX = minX; MinY = minY; MaxX = maxX; MaxY = maxY; }
        internal bool Conflicts(PlanBounds other, double clearance)
        {
            return !(MaxX + clearance <= other.MinX || other.MaxX + clearance <= MinX ||
                MaxY + clearance <= other.MinY || other.MaxY + clearance <= MinY);
        }
    }

    internal sealed class RectangularPocket
    {
        internal double X, Y, Width, Height, Depth;
        internal double AreaMm2 { get { return Width * Height; } }
        internal PlanBounds Bounds { get { return new PlanBounds(X - Width / 2.0, Y - Height / 2.0, X + Width / 2.0, Y + Height / 2.0); } }
        internal object ToJson()
        {
            return Json.Obj("x_mm", X, "y_mm", Y, "width_mm", Width,
                "height_mm", Height, "depth_mm", Depth);
        }
    }

    internal sealed class CircularPocket
    {
        internal double X, Y, Diameter, Depth;
        internal double Radius { get { return Diameter / 2.0; } }
        internal double AreaMm2 { get { return Math.PI * Radius * Radius; } }
        internal PlanBounds Bounds { get { return new PlanBounds(X - Radius, Y - Radius, X + Radius, Y + Radius); } }
        internal object ToJson()
        { return Json.Obj("x_mm", X, "y_mm", Y, "diameter_mm", Diameter, "depth_mm", Depth); }
    }

    internal sealed class StraightSlot
    {
        internal double X1, Y1, X2, Y2, Width, Depth;
        internal bool Through;
        internal double Radius { get { return Width / 2.0; } }
        internal double LengthMm { get { double dx = X2 - X1, dy = Y2 - Y1; return Math.Sqrt(dx * dx + dy * dy); } }
        internal double AreaMm2 { get { return LengthMm * Width + Math.PI * Radius * Radius; } }
        internal PlanBounds Bounds
        {
            get { return new PlanBounds(Math.Min(X1, X2) - Radius, Math.Min(Y1, Y2) - Radius,
                Math.Max(X1, X2) + Radius, Math.Max(Y1, Y2) + Radius); }
        }
        internal object ToJson()
        {
            return Json.Obj("x1_mm", X1, "y1_mm", Y1, "x2_mm", X2, "y2_mm", Y2,
                "width_mm", Width, "cut_type", Through ? "through" : "blind",
                "depth_mm", Through ? null : (object)Depth);
        }
    }

    internal sealed class RectangularBoss
    {
        internal double X, Y, Width, Height, Extrusion, CornerSize;
        internal string CornerStyle;
        internal double AreaMm2
        {
            get
            {
                if (CornerStyle == "chamfer") return Width * Height - 2.0 * CornerSize * CornerSize;
                if (CornerStyle == "round") return Width * Height - (4.0 - Math.PI) * CornerSize * CornerSize;
                return Width * Height;
            }
        }
        internal PlanBounds Bounds
        {
            get { return new PlanBounds(X - Width / 2.0, Y - Height / 2.0,
                X + Width / 2.0, Y + Height / 2.0); }
        }
        internal object ToJson()
        {
            return Json.Obj("x_mm", X, "y_mm", Y, "width_mm", Width,
                "height_mm", Height, "extrusion_mm", Extrusion,
                "corner_style", CornerStyle, "corner_size_mm", CornerStyle == null ? null : (object)CornerSize);
        }
    }

    internal sealed class CircularBoss
    {
        internal double X, Y, Diameter, Extrusion;
        internal double Radius { get { return Diameter / 2.0; } }
        internal double AreaMm2 { get { return Math.PI * Radius * Radius; } }
        internal PlanBounds Bounds
        {
            get { return new PlanBounds(X - Radius, Y - Radius, X + Radius, Y + Radius); }
        }
        internal object ToJson()
        {
            return Json.Obj("x_mm", X, "y_mm", Y, "diameter_mm", Diameter,
                "extrusion_mm", Extrusion);
        }
    }

    // Strict, versioned input language for one new prismatic part. This is data,
    // never code: no paths, feature names, macros or arbitrary COM members exist.
    internal sealed class PartPlan
    {
        internal const string BasicVersion = "1";
        internal const string ParametricVersion = "2";
        internal const string CutVersion = "3";
        internal const string BossVersion = "4";
        internal const string CornerBossVersion = "5";
        internal const string CurrentVersion = "6";
        internal const string FilletVersion = "6";
        internal const double ClearanceMm = 0.05;
        internal string PlanVersion;
        internal string ProfileType;
        internal double WidthMm, HeightMm, DiameterMm, ThicknessMm;
        internal double OuterAreaMm2, SpanXMm, SpanYMm, BaseExpectedVolumeM3,
            BossAddedVolumeM3, ExpectedAfterBossesVolumeM3, ExpectedVolumeM3, MaxBossExtrusionMm;
        internal CircularHolePattern Pattern;
        internal NewPartProperties Properties;
        internal string MaterialName;
        internal readonly List<PlanPoint> Points = new List<PlanPoint>();
        internal readonly List<PlanHole> Holes = new List<PlanHole>();
        internal readonly List<RectangularPocket> RectangularPockets = new List<RectangularPocket>();
        internal readonly List<CircularPocket> CircularPockets = new List<CircularPocket>();
        internal readonly List<StraightSlot> StraightSlots = new List<StraightSlot>();
        internal readonly List<RectangularBoss> RectangularBosses = new List<RectangularBoss>();
        internal readonly List<CircularBoss> CircularBosses = new List<CircularBoss>();

        static void ExactKeys(Dictionary<string, object> value, string label, params string[] allowedNames)
        {
            var allowed = new HashSet<string>(allowedNames, StringComparer.Ordinal);
            foreach (string key in value.Keys)
                if (!allowed.Contains(key)) throw new Fault("INVALID_ARGUMENTS", label + " contains an unexpected field: " + key);
        }
        static Dictionary<string, object> ObjectAt(Dictionary<string, object> value, string key)
        {
            var result = Json.At(value, key) as Dictionary<string, object>;
            if (result == null) throw new Fault("INVALID_ARGUMENTS", key + " must be an object.");
            return result;
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
        static double Cross(PlanPoint a, PlanPoint b, PlanPoint c)
        { return (b.X - a.X) * (c.Y - a.Y) - (b.Y - a.Y) * (c.X - a.X); }
        static bool Between(double a, double b, double value)
        { return value >= Math.Min(a, b) - 1e-9 && value <= Math.Max(a, b) + 1e-9; }
        static bool OnSegment(PlanPoint a, PlanPoint b, PlanPoint p)
        { return Math.Abs(Cross(a, b, p)) <= 1e-9 && Between(a.X, b.X, p.X) && Between(a.Y, b.Y, p.Y); }
        static int Side(double value) { return value > 1e-9 ? 1 : value < -1e-9 ? -1 : 0; }
        static bool SegmentsIntersect(PlanPoint a, PlanPoint b, PlanPoint c, PlanPoint d)
        {
            int abC = Side(Cross(a, b, c)), abD = Side(Cross(a, b, d));
            int cdA = Side(Cross(c, d, a)), cdB = Side(Cross(c, d, b));
            if (abC == 0 && OnSegment(a, b, c)) return true;
            if (abD == 0 && OnSegment(a, b, d)) return true;
            if (cdA == 0 && OnSegment(c, d, a)) return true;
            if (cdB == 0 && OnSegment(c, d, b)) return true;
            return abC != abD && cdA != cdB;
        }
        static double DistanceToSegment(PlanPoint p, PlanPoint a, PlanPoint b)
        {
            double dx = b.X - a.X, dy = b.Y - a.Y;
            double length2 = dx * dx + dy * dy;
            if (length2 <= 1e-12) return Math.Sqrt((p.X - a.X) * (p.X - a.X) + (p.Y - a.Y) * (p.Y - a.Y));
            double t = ((p.X - a.X) * dx + (p.Y - a.Y) * dy) / length2;
            t = Math.Max(0.0, Math.Min(1.0, t));
            double x = a.X + t * dx, y = a.Y + t * dy;
            return Math.Sqrt((p.X - x) * (p.X - x) + (p.Y - y) * (p.Y - y));
        }
        static bool PointInsidePolygon(PlanPoint point, List<PlanPoint> polygon)
        {
            bool inside = false;
            for (int i = 0, j = polygon.Count - 1; i < polygon.Count; j = i++)
            {
                PlanPoint a = polygon[i], b = polygon[j];
                if (((a.Y > point.Y) != (b.Y > point.Y)) &&
                    point.X < (b.X - a.X) * (point.Y - a.Y) / (b.Y - a.Y) + a.X)
                    inside = !inside;
            }
            return inside;
        }
        static double PolygonArea(List<PlanPoint> points)
        {
            double twice = 0.0;
            for (int i = 0; i < points.Count; i++)
            {
                PlanPoint a = points[i], b = points[(i + 1) % points.Count];
                twice += a.X * b.Y - b.X * a.Y;
            }
            return Math.Abs(twice) / 2.0;
        }
        static void ValidateSimplePolygon(List<PlanPoint> points)
        {
            int count = points.Count;
            for (int i = 0; i < count; i++)
            {
                PlanPoint a = points[i], b = points[(i + 1) % count];
                double dx = a.X - b.X, dy = a.Y - b.Y;
                if (Math.Sqrt(dx * dx + dy * dy) < 0.1)
                    throw new Fault("INVALID_ARGUMENTS", "Polygon has a duplicate or shorter-than-0.1-mm edge.");
            }
            for (int i = 0; i < count; i++)
                for (int j = i + 1; j < count; j++)
                {
                    if (j == i + 1 || (i == 0 && j == count - 1)) continue;
                    if (SegmentsIntersect(points[i], points[(i + 1) % count], points[j], points[(j + 1) % count]))
                        throw new Fault("INVALID_ARGUMENTS", "Polygon edges intersect. Supply one simple closed outer contour.");
                }
        }
        static void ComputeAndApplyCornerFinishing(PartPlan plan)
        {
            List<PlanPoint> points = plan.Points;
            int count = points.Count;
            bool anyCorner = false;
            foreach (PlanPoint p in points) if (p.CornerStyle != null) anyCorner = true;
            if (!anyCorner) return;

            double signedTwice = 0.0;
            for (int i = 0; i < count; i++)
            {
                PlanPoint a = points[i], b = points[(i + 1) % count];
                signedTwice += a.X * b.Y - b.X * a.Y;
            }
            double orientationSign = signedTwice >= 0 ? 1.0 : -1.0;
            double totalRemovedArea = 0.0;

            for (int i = 0; i < count; i++)
            {
                PlanPoint cur = points[i];
                if (cur.CornerStyle == null) continue;
                PlanPoint prev = points[(i - 1 + count) % count];
                PlanPoint next = points[(i + 1) % count];
                double inX = prev.X - cur.X, inY = prev.Y - cur.Y;
                double outX = next.X - cur.X, outY = next.Y - cur.Y;
                double inLen = Math.Sqrt(inX * inX + inY * inY);
                double outLen = Math.Sqrt(outX * outX + outY * outY);
                if (inLen < 1e-9 || outLen < 1e-9)
                    throw new Fault("INVALID_ARGUMENTS", "Polygon corner finishing point has a zero-length adjacent edge.");

                double edgeCross = (cur.X - prev.X) * (next.Y - cur.Y) -
                    (cur.Y - prev.Y) * (next.X - cur.X);
                if (Math.Abs(edgeCross) < 1e-6)
                    throw new Fault("INVALID_ARGUMENTS", "Corner finishing cannot be applied to a collinear vertex.");
                bool convex = (edgeCross >= 0) == (orientationSign >= 0);
                if (!convex)
                    throw new Fault("INVALID_ARGUMENTS", "Corner finishing can only be applied to convex polygon vertices.");

                double cosTheta = (inX * outX + inY * outY) / (inLen * outLen);
                cosTheta = Math.Max(-1.0, Math.Min(1.0, cosTheta));
                double theta = Math.Acos(cosTheta);
                if (theta < 0.05 || theta > Math.PI - 0.05)
                    throw new Fault("INVALID_ARGUMENTS", "Corner finishing vertex angle is too sharp or too flat.");
                cur.InteriorAngleRad = theta;

                double size = cur.CornerSizeMm;
                double tangentLength, removedArea;
                if (cur.CornerStyle == "round")
                {
                    tangentLength = size / Math.Tan(theta / 2.0);
                    removedArea = size * size *
                        (1.0 / Math.Tan(theta / 2.0) - (Math.PI - theta) / 2.0);
                    double bisectorX = inX / inLen + outX / outLen;
                    double bisectorY = inY / inLen + outY / outLen;
                    double bisectorLen = Math.Sqrt(bisectorX * bisectorX + bisectorY * bisectorY);
                    double centerDistance = size / Math.Sin(theta / 2.0);
                    cur.ArcCenterXMm = cur.X + bisectorX / bisectorLen * centerDistance;
                    cur.ArcCenterYMm = cur.Y + bisectorY / bisectorLen * centerDistance;
                }
                else
                {
                    tangentLength = size;
                    removedArea = 0.5 * size * size * Math.Sin(theta);
                }
                if (tangentLength <= 0.0 || double.IsNaN(tangentLength) || double.IsInfinity(tangentLength))
                    throw new Fault("INVALID_ARGUMENTS", "corner_size_mm produced invalid corner geometry.");

                cur.TangentLengthMm = tangentLength;
                cur.CornerAreaRemovedMm2 = removedArea;
                cur.TangentInXMm = cur.X + inX / inLen * tangentLength;
                cur.TangentInYMm = cur.Y + inY / inLen * tangentLength;
                cur.TangentOutXMm = cur.X + outX / outLen * tangentLength;
                cur.TangentOutYMm = cur.Y + outY / outLen * tangentLength;
                totalRemovedArea += removedArea;
            }

            for (int i = 0; i < count; i++)
            {
                PlanPoint a = points[i], b = points[(i + 1) % count];
                double edgeLen = Math.Sqrt((b.X - a.X) * (b.X - a.X) + (b.Y - a.Y) * (b.Y - a.Y));
                double consumedFromA = a.CornerStyle != null ? a.TangentLengthMm : 0.0;
                double consumedFromB = b.CornerStyle != null ? b.TangentLengthMm : 0.0;
                if (consumedFromA + consumedFromB > edgeLen - ClearanceMm)
                    throw new Fault("INVALID_ARGUMENTS", "Corner finishing at adjacent vertices consumes more than the shared edge length.");
            }

            plan.OuterAreaMm2 -= totalRemovedArea;
            if (plan.OuterAreaMm2 < 25.0)
                throw new Fault("INVALID_ARGUMENTS", "Polygon corner finishing leaves too little remaining area.");
        }
        static List<PlanPoint> FinishedPolygonBoundary(List<PlanPoint> points)
        {
            var boundary = new List<PlanPoint>();
            for (int i = 0; i < points.Count; i++)
            {
                PlanPoint a = points[i], b = points[(i + 1) % points.Count];
                boundary.Add(new PlanPoint(
                    a.CornerStyle == null ? a.X : a.TangentOutXMm,
                    a.CornerStyle == null ? a.Y : a.TangentOutYMm));
                boundary.Add(new PlanPoint(
                    b.CornerStyle == null ? b.X : b.TangentInXMm,
                    b.CornerStyle == null ? b.Y : b.TangentInYMm));
                if (b.CornerStyle == "chamfer")
                    boundary.Add(new PlanPoint(b.TangentOutXMm, b.TangentOutYMm));
                else if (b.CornerStyle == "round")
                {
                    double start = Math.Atan2(b.TangentInYMm - b.ArcCenterYMm,
                        b.TangentInXMm - b.ArcCenterXMm);
                    double end = Math.Atan2(b.TangentOutYMm - b.ArcCenterYMm,
                        b.TangentOutXMm - b.ArcCenterXMm);
                    double cross = (b.TangentInXMm - b.ArcCenterXMm) *
                        (b.TangentOutYMm - b.ArcCenterYMm) -
                        (b.TangentInYMm - b.ArcCenterYMm) *
                        (b.TangentOutXMm - b.ArcCenterXMm);
                    double sweep = end - start;
                    if (cross >= 0) { while (sweep <= 0) sweep += 2.0 * Math.PI; }
                    else { while (sweep >= 0) sweep -= 2.0 * Math.PI; }
                    int steps = Math.Max(2, (int)Math.Ceiling(Math.Abs(sweep) * 180.0 / Math.PI));
                    for (int step = 1; step <= steps; step++)
                    {
                        double angle = start + sweep * step / steps;
                        boundary.Add(new PlanPoint(
                            b.ArcCenterXMm + b.CornerSizeMm * Math.Cos(angle),
                            b.ArcCenterYMm + b.CornerSizeMm * Math.Sin(angle)));
                    }
                }
            }
            return boundary;
        }
        bool ContainsHole(PlanHole hole)
        {
            double required = hole.Radius + ClearanceMm;
            if (ProfileType == "rectangle")
                return Math.Abs(hole.X) + required <= WidthMm / 2.0 && Math.Abs(hole.Y) + required <= HeightMm / 2.0;
            if (ProfileType == "circle")
                return Math.Sqrt(hole.X * hole.X + hole.Y * hole.Y) + required <= DiameterMm / 2.0;
            var center = new PlanPoint(hole.X, hole.Y);
            List<PlanPoint> boundary = FinishedPolygonBoundary(Points);
            if (!PointInsidePolygon(center, boundary)) return false;
            for (int i = 0; i < boundary.Count; i++)
                if (DistanceToSegment(center, boundary[i], boundary[(i + 1) % boundary.Count]) < required) return false;
            return true;
        }

        void AddValidatedHole(PlanHole parsed)
        {
            if (Holes.Count >= 32)
                throw new Fault("INVALID_ARGUMENTS", "At most 32 circular holes are allowed in total.");
            if (!ContainsHole(parsed))
                throw new Fault("INVALID_ARGUMENTS", "Every hole must remain inside the outer profile with at least 0.05 mm clearance.");
            foreach (PlanHole existing in Holes)
            {
                double dx = existing.X - parsed.X, dy = existing.Y - parsed.Y;
                if (Math.Sqrt(dx * dx + dy * dy) < existing.Radius + parsed.Radius + ClearanceMm)
                    throw new Fault("INVALID_ARGUMENTS", "Circular holes overlap or touch each other.");
            }
            Holes.Add(parsed);
        }

        bool ContainsRectangle(PlanBounds bounds)
        {
            if (ProfileType == "rectangle")
                return bounds.MinX >= -WidthMm / 2.0 + ClearanceMm && bounds.MaxX <= WidthMm / 2.0 - ClearanceMm &&
                    bounds.MinY >= -HeightMm / 2.0 + ClearanceMm && bounds.MaxY <= HeightMm / 2.0 - ClearanceMm;
            if (ProfileType == "circle")
            {
                double allowed = DiameterMm / 2.0 - ClearanceMm;
                foreach (double x in new[] { bounds.MinX, bounds.MaxX })
                    foreach (double y in new[] { bounds.MinY, bounds.MaxY })
                        if (Math.Sqrt(x * x + y * y) > allowed) return false;
                return true;
            }
            return false;
        }

        bool ContainsSlot(StraightSlot slot)
        {
            double required = slot.Radius + ClearanceMm;
            if (ProfileType == "rectangle")
                return Math.Abs(slot.X1) + required <= WidthMm / 2.0 && Math.Abs(slot.X2) + required <= WidthMm / 2.0 &&
                    Math.Abs(slot.Y1) + required <= HeightMm / 2.0 && Math.Abs(slot.Y2) + required <= HeightMm / 2.0;
            if (ProfileType == "circle")
                return Math.Sqrt(slot.X1 * slot.X1 + slot.Y1 * slot.Y1) + required <= DiameterMm / 2.0 &&
                    Math.Sqrt(slot.X2 * slot.X2 + slot.Y2 * slot.Y2) + required <= DiameterMm / 2.0;
            return false;
        }

        static void AddNonConflictingBounds(List<PlanBounds> occupied, PlanBounds candidate, string label)
        {
            foreach (PlanBounds existing in occupied)
                if (existing.Conflicts(candidate, ClearanceMm))
                    throw new Fault("INVALID_ARGUMENTS", label + " overlaps another hole, pocket or slot, or is closer than 0.05 mm.");
            occupied.Add(candidate);
        }

        internal static PartPlan Parse(Dictionary<string, object> args)
        {
            if (args == null) throw new Fault("INVALID_ARGUMENTS", "arguments must be an object.");
            string version = StringAt(args, "plan_version");
            if (version != BasicVersion && version != ParametricVersion && version != CutVersion &&
                version != BossVersion && version != CornerBossVersion && version != FilletVersion)
                throw new Fault("INVALID_ARGUMENTS", "Unsupported prismatic plan version. Use plan_version=1, 2, 3, 4, 5 or 6.");
            if (version == BasicVersion)
                ExactKeys(args, "plan", "plan_version", "outer_profile", "thickness_mm", "holes");
            else if (version == ParametricVersion)
                ExactKeys(args, "plan", "plan_version", "outer_profile", "thickness_mm", "holes",
                    "circular_hole_pattern", "properties", "material");
            else if (version == CutVersion)
                ExactKeys(args, "plan", "plan_version", "outer_profile", "thickness_mm", "holes",
                    "circular_hole_pattern", "properties", "material", "rectangular_pockets",
                    "circular_pockets", "straight_slots");
            else if (version == BossVersion)
                ExactKeys(args, "plan", "plan_version", "outer_profile", "thickness_mm", "holes",
                    "circular_hole_pattern", "properties", "material", "rectangular_pockets",
                    "circular_pockets", "straight_slots", "rectangular_bosses", "circular_bosses");
            else
                ExactKeys(args, "plan", "plan_version", "outer_profile", "thickness_mm", "holes",
                    "circular_hole_pattern", "properties", "material", "rectangular_pockets",
                    "circular_pockets", "straight_slots", "rectangular_bosses", "circular_bosses");

            var plan = new PartPlan();
            plan.PlanVersion = version;
            plan.ThicknessMm = NumberAt(args, "thickness_mm", 0.5, 500.0);
            var profile = ObjectAt(args, "outer_profile");
            plan.ProfileType = StringAt(profile, "type").ToLowerInvariant();
            if (plan.ProfileType == "rectangle")
            {
                ExactKeys(profile, "outer_profile", "type", "width_mm", "height_mm");
                plan.WidthMm = NumberAt(profile, "width_mm", 5.0, 2000.0);
                plan.HeightMm = NumberAt(profile, "height_mm", 5.0, 2000.0);
                plan.SpanXMm = plan.WidthMm; plan.SpanYMm = plan.HeightMm;
                plan.OuterAreaMm2 = plan.WidthMm * plan.HeightMm;
            }
            else if (plan.ProfileType == "circle")
            {
                ExactKeys(profile, "outer_profile", "type", "diameter_mm");
                plan.DiameterMm = NumberAt(profile, "diameter_mm", 5.0, 2000.0);
                plan.SpanXMm = plan.DiameterMm; plan.SpanYMm = plan.DiameterMm;
                plan.OuterAreaMm2 = Math.PI * plan.DiameterMm * plan.DiameterMm / 4.0;
            }
            else if (plan.ProfileType == "polygon")
            {
                ExactKeys(profile, "outer_profile", "type", "points_mm");
                Array rawPoints = ArrayAt(profile, "points_mm", true);
                if (rawPoints.Length < 3 || rawPoints.Length > 24)
                    throw new Fault("INVALID_ARGUMENTS", "Polygon requires 3 to 24 points.");
                bool allowCorners = version == FilletVersion;
                double minX = double.MaxValue, minY = double.MaxValue, maxX = double.MinValue, maxY = double.MinValue;
                foreach (object rawPoint in rawPoints)
                {
                    var point = rawPoint as Dictionary<string, object>;
                    if (point == null) throw new Fault("INVALID_ARGUMENTS", "Each polygon point must be an object.");
                    if (allowCorners)
                        ExactKeys(point, "polygon point", "x_mm", "y_mm", "corner_style", "corner_size_mm");
                    else
                        ExactKeys(point, "polygon point", "x_mm", "y_mm");
                    double x = NumberAt(point, "x_mm", -1000.0, 1000.0);
                    double y = NumberAt(point, "y_mm", -1000.0, 1000.0);
                    var planPoint = new PlanPoint(x, y);
                    object rawCornerStyle = Json.At(point, "corner_style");
                    object rawCornerSize = Json.At(point, "corner_size_mm");
                    if (rawCornerStyle != null || rawCornerSize != null)
                    {
                        if (!allowCorners)
                            throw new Fault("INVALID_ARGUMENTS", "Polygon corner finishing requires prismatic plan_version=6.");
                        string style = rawCornerStyle as string;
                        if (style == null) throw new Fault("INVALID_ARGUMENTS", "corner_style must be chamfer or round.");
                        style = style.Trim().ToLowerInvariant();
                        if (style != "chamfer" && style != "round")
                            throw new Fault("INVALID_ARGUMENTS", "corner_style must be chamfer or round.");
                        planPoint.CornerStyle = style;
                        planPoint.CornerSizeMm = NumberAt(point, "corner_size_mm", 0.1, 500.0);
                    }
                    plan.Points.Add(planPoint);
                    minX = Math.Min(minX, x); minY = Math.Min(minY, y);
                    maxX = Math.Max(maxX, x); maxY = Math.Max(maxY, y);
                }
                ValidateSimplePolygon(plan.Points);
                plan.SpanXMm = maxX - minX; plan.SpanYMm = maxY - minY;
                plan.OuterAreaMm2 = PolygonArea(plan.Points);
                if (plan.SpanXMm < 1.0 || plan.SpanYMm < 1.0 || plan.OuterAreaMm2 < 25.0)
                    throw new Fault("INVALID_ARGUMENTS", "Polygon is too small or degenerate.");
                if (allowCorners) ComputeAndApplyCornerFinishing(plan);
            }
            else throw new Fault("INVALID_ARGUMENTS", "outer_profile.type must be rectangle, circle or polygon.");

            Array rawHoles = ArrayAt(args, "holes", false);
            if (rawHoles.Length > 32) throw new Fault("INVALID_ARGUMENTS", "At most 32 circular holes are allowed.");
            foreach (object rawHole in rawHoles)
            {
                var hole = rawHole as Dictionary<string, object>;
                if (hole == null) throw new Fault("INVALID_ARGUMENTS", "Each hole must be an object.");
                ExactKeys(hole, "hole", "x_mm", "y_mm", "diameter_mm");
                var parsed = new PlanHole(NumberAt(hole, "x_mm", -1000.0, 1000.0),
                    NumberAt(hole, "y_mm", -1000.0, 1000.0), NumberAt(hole, "diameter_mm", 1.0, 500.0));
                plan.AddValidatedHole(parsed);
            }

            if (version != BasicVersion)
            {
                object patternRaw = Json.At(args, "circular_hole_pattern");
                if (patternRaw != null)
                {
                    var pattern = patternRaw as Dictionary<string, object>;
                    if (pattern == null) throw new Fault("INVALID_ARGUMENTS", "circular_hole_pattern must be an object.");
                    ExactKeys(pattern, "circular_hole_pattern", "pitch_circle_diameter_mm",
                        "hole_diameter_mm", "hole_count", "start_angle_deg");
                    plan.Pattern = new CircularHolePattern {
                        PitchCircleDiameter = NumberAt(pattern, "pitch_circle_diameter_mm", 1.0, 2000.0),
                        HoleDiameter = NumberAt(pattern, "hole_diameter_mm", 1.0, 500.0),
                        HoleCount = IntegerAt(pattern, "hole_count", 2, 32),
                        StartAngleDegrees = NumberAt(pattern, "start_angle_deg", -360.0, 360.0)
                    };
                    double patternRadius = plan.Pattern.PitchCircleDiameter / 2.0;
                    for (int i = 0; i < plan.Pattern.HoleCount; i++)
                    {
                        double angle = (plan.Pattern.StartAngleDegrees + 360.0 * i / plan.Pattern.HoleCount) * Math.PI / 180.0;
                        double x = patternRadius * Math.Cos(angle), y = patternRadius * Math.Sin(angle);
                        if (Math.Abs(x) < 1e-10) x = 0.0;
                        if (Math.Abs(y) < 1e-10) y = 0.0;
                        plan.AddValidatedHole(new PlanHole(x, y, plan.Pattern.HoleDiameter));
                    }
                }

                object propertiesRaw = Json.At(args, "properties");
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

                object materialRaw = Json.At(args, "material");
                if (materialRaw != null)
                {
                    string material = materialRaw as string;
                    if (!string.Equals(material == null ? null : material.Trim(), "AISI 304", StringComparison.OrdinalIgnoreCase))
                        throw new Fault("INVALID_ARGUMENTS", "This connector version supports only material=AISI 304.");
                    plan.MaterialName = "AISI 304";
                }
            }

            var occupied = new List<PlanBounds>();
            foreach (PlanHole hole in plan.Holes)
                occupied.Add(new PlanBounds(hole.X - hole.Radius, hole.Y - hole.Radius,
                    hole.X + hole.Radius, hole.Y + hole.Radius));

            if (version == CutVersion || version == BossVersion ||
                version == CornerBossVersion || version == FilletVersion)
            {
                Array rawRectangular = ArrayAt(args, "rectangular_pockets", false);
                Array rawCircular = ArrayAt(args, "circular_pockets", false);
                Array rawSlots = ArrayAt(args, "straight_slots", false);
                if (rawRectangular.Length > 8 || rawCircular.Length > 8 || rawSlots.Length > 8 ||
                    rawRectangular.Length + rawCircular.Length + rawSlots.Length > 16)
                    throw new Fault("INVALID_ARGUMENTS", "Prismatic Plans v3-v6 allow at most 8 cuts of each kind and 16 cuts in total.");
                if (plan.ProfileType == "polygon" &&
                    (rawRectangular.Length > 0 || rawCircular.Length > 0 || rawSlots.Length > 0))
                    throw new Fault("INVALID_ARGUMENTS", "Prismatic Plan pockets and slots currently require a rectangle or circle outer profile.");

                foreach (object item in rawRectangular)
                {
                    var value = item as Dictionary<string, object>;
                    if (value == null) throw new Fault("INVALID_ARGUMENTS", "Each rectangular pocket must be an object.");
                    ExactKeys(value, "rectangular pocket", "x_mm", "y_mm", "width_mm", "height_mm", "depth_mm");
                    var pocket = new RectangularPocket {
                        X = NumberAt(value, "x_mm", -1000.0, 1000.0),
                        Y = NumberAt(value, "y_mm", -1000.0, 1000.0),
                        Width = NumberAt(value, "width_mm", 1.0, 1000.0),
                        Height = NumberAt(value, "height_mm", 1.0, 1000.0),
                        Depth = NumberAt(value, "depth_mm", 0.1, plan.ThicknessMm - 0.1)
                    };
                    if (!plan.ContainsRectangle(pocket.Bounds))
                        throw new Fault("INVALID_ARGUMENTS", "Every rectangular pocket must remain inside the outer profile with at least 0.05 mm clearance.");
                    AddNonConflictingBounds(occupied, pocket.Bounds, "A rectangular pocket");
                    plan.RectangularPockets.Add(pocket);
                }

                foreach (object item in rawCircular)
                {
                    var value = item as Dictionary<string, object>;
                    if (value == null) throw new Fault("INVALID_ARGUMENTS", "Each circular pocket must be an object.");
                    ExactKeys(value, "circular pocket", "x_mm", "y_mm", "diameter_mm", "depth_mm");
                    var pocket = new CircularPocket {
                        X = NumberAt(value, "x_mm", -1000.0, 1000.0),
                        Y = NumberAt(value, "y_mm", -1000.0, 1000.0),
                        Diameter = NumberAt(value, "diameter_mm", 1.0, 500.0),
                        Depth = NumberAt(value, "depth_mm", 0.1, plan.ThicknessMm - 0.1)
                    };
                    if (!plan.ContainsHole(new PlanHole(pocket.X, pocket.Y, pocket.Diameter)))
                        throw new Fault("INVALID_ARGUMENTS", "Every circular pocket must remain inside the outer profile with at least 0.05 mm clearance.");
                    AddNonConflictingBounds(occupied, pocket.Bounds, "A circular pocket");
                    plan.CircularPockets.Add(pocket);
                }

                foreach (object item in rawSlots)
                {
                    var value = item as Dictionary<string, object>;
                    if (value == null) throw new Fault("INVALID_ARGUMENTS", "Each straight slot must be an object.");
                    ExactKeys(value, "straight slot", "x1_mm", "y1_mm", "x2_mm", "y2_mm",
                        "width_mm", "cut_type", "depth_mm");
                    string cutType = StringAt(value, "cut_type").ToLowerInvariant();
                    if (cutType != "through" && cutType != "blind")
                        throw new Fault("INVALID_ARGUMENTS", "straight slot cut_type must be through or blind.");
                    bool through = cutType == "through";
                    if (through && Json.At(value, "depth_mm") != null)
                        throw new Fault("INVALID_ARGUMENTS", "A through straight slot must not contain depth_mm.");
                    var slot = new StraightSlot {
                        X1 = NumberAt(value, "x1_mm", -1000.0, 1000.0),
                        Y1 = NumberAt(value, "y1_mm", -1000.0, 1000.0),
                        X2 = NumberAt(value, "x2_mm", -1000.0, 1000.0),
                        Y2 = NumberAt(value, "y2_mm", -1000.0, 1000.0),
                        Width = NumberAt(value, "width_mm", 1.0, 500.0),
                        Through = through,
                        Depth = through ? plan.ThicknessMm : NumberAt(value, "depth_mm", 0.1, plan.ThicknessMm - 0.1)
                    };
                    if (slot.LengthMm < 1.0)
                        throw new Fault("INVALID_ARGUMENTS", "Straight-slot arc centres must be at least 1 mm apart.");
                    if (slot.LengthMm + 1e-9 < slot.Width)
                        throw new Fault("INVALID_ARGUMENTS", "Straight-slot arc-centre distance must be at least its width in this version.");
                    if (!plan.ContainsSlot(slot))
                        throw new Fault("INVALID_ARGUMENTS", "Every straight slot must remain inside the outer profile with at least 0.05 mm clearance.");
                    AddNonConflictingBounds(occupied, slot.Bounds, "A straight slot");
                    plan.StraightSlots.Add(slot);
                }
            }

            if (version == BossVersion || version == CornerBossVersion || version == FilletVersion)
            {
                Array rawRectangularBosses = ArrayAt(args, "rectangular_bosses", false);
                Array rawCircularBosses = ArrayAt(args, "circular_bosses", false);
                if (rawRectangularBosses.Length > 8 || rawCircularBosses.Length > 8 ||
                    rawRectangularBosses.Length + rawCircularBosses.Length > 12)
                    throw new Fault("INVALID_ARGUMENTS", "Plans v4/v5 allow at most 8 bosses of each kind and 12 bosses in total.");
                if (plan.ProfileType == "polygon" &&
                    (rawRectangularBosses.Length > 0 || rawCircularBosses.Length > 0))
                    throw new Fault("INVALID_ARGUMENTS", "Prismatic bosses currently require a rectangle or circle outer profile.");

                foreach (object item in rawRectangularBosses)
                {
                    var value = item as Dictionary<string, object>;
                    if (value == null) throw new Fault("INVALID_ARGUMENTS", "Each rectangular boss must be an object.");
                    if (version == CornerBossVersion || version == FilletVersion)
                        ExactKeys(value, "rectangular boss", "x_mm", "y_mm", "width_mm", "height_mm", "extrusion_mm",
                            "corner_style", "corner_size_mm");
                    else
                        ExactKeys(value, "rectangular boss", "x_mm", "y_mm", "width_mm", "height_mm", "extrusion_mm");
                    var boss = new RectangularBoss {
                        X = NumberAt(value, "x_mm", -1000.0, 1000.0),
                        Y = NumberAt(value, "y_mm", -1000.0, 1000.0),
                        Width = NumberAt(value, "width_mm", 1.0, 1000.0),
                        Height = NumberAt(value, "height_mm", 1.0, 1000.0),
                        Extrusion = NumberAt(value, "extrusion_mm", 0.1, 500.0)
                    };
                    object rawCornerStyle = Json.At(value, "corner_style");
                    object rawCornerSize = Json.At(value, "corner_size_mm");
                    if (rawCornerStyle != null || rawCornerSize != null)
                    {
                        if (version != CornerBossVersion && version != FilletVersion)
                            throw new Fault("INVALID_ARGUMENTS", "Corner finishing requires prismatic plan_version=5 or 6.");
                        string style = rawCornerStyle as string;
                        if (style == null) throw new Fault("INVALID_ARGUMENTS", "corner_style must be chamfer or round.");
                        style = style.Trim().ToLowerInvariant();
                        if (style != "chamfer" && style != "round")
                            throw new Fault("INVALID_ARGUMENTS", "corner_style must be chamfer or round.");
                        double maximumCorner = Math.Min(boss.Width, boss.Height) / 2.0 - 0.1;
                        boss.CornerStyle = style;
                        boss.CornerSize = NumberAt(value, "corner_size_mm", 0.1, maximumCorner);
                    }
                    if (!plan.ContainsRectangle(boss.Bounds))
                        throw new Fault("INVALID_ARGUMENTS", "Every rectangular boss must remain inside the outer profile with at least 0.05 mm clearance.");
                    AddNonConflictingBounds(occupied, boss.Bounds, "A rectangular boss");
                    plan.RectangularBosses.Add(boss);
                }

                foreach (object item in rawCircularBosses)
                {
                    var value = item as Dictionary<string, object>;
                    if (value == null) throw new Fault("INVALID_ARGUMENTS", "Each circular boss must be an object.");
                    ExactKeys(value, "circular boss", "x_mm", "y_mm", "diameter_mm", "extrusion_mm");
                    var boss = new CircularBoss {
                        X = NumberAt(value, "x_mm", -1000.0, 1000.0),
                        Y = NumberAt(value, "y_mm", -1000.0, 1000.0),
                        Diameter = NumberAt(value, "diameter_mm", 1.0, 500.0),
                        Extrusion = NumberAt(value, "extrusion_mm", 0.1, 500.0)
                    };
                    if (!plan.ContainsHole(new PlanHole(boss.X, boss.Y, boss.Diameter)))
                        throw new Fault("INVALID_ARGUMENTS", "Every circular boss must remain inside the outer profile with at least 0.05 mm clearance.");
                    AddNonConflictingBounds(occupied, boss.Bounds, "A circular boss");
                    plan.CircularBosses.Add(boss);
                }
            }

            double removedArea = 0.0;
            foreach (PlanHole hole in plan.Holes) removedArea += Math.PI * hole.Radius * hole.Radius;
            double netArea = plan.OuterAreaMm2 - removedArea;
            if (netArea <= 1.0) throw new Fault("INVALID_ARGUMENTS", "The holes remove the entire profile.");
            plan.BaseExpectedVolumeM3 = netArea * plan.ThicknessMm * 1e-9;
            double addedBossMm3 = 0.0;
            foreach (RectangularBoss boss in plan.RectangularBosses)
            {
                addedBossMm3 += boss.AreaMm2 * boss.Extrusion;
                plan.MaxBossExtrusionMm = Math.Max(plan.MaxBossExtrusionMm, boss.Extrusion);
            }
            foreach (CircularBoss boss in plan.CircularBosses)
            {
                addedBossMm3 += boss.AreaMm2 * boss.Extrusion;
                plan.MaxBossExtrusionMm = Math.Max(plan.MaxBossExtrusionMm, boss.Extrusion);
            }
            plan.BossAddedVolumeM3 = addedBossMm3 * 1e-9;
            plan.ExpectedAfterBossesVolumeM3 = plan.BaseExpectedVolumeM3 + plan.BossAddedVolumeM3;
            double extraRemovedMm3 = 0.0;
            foreach (RectangularPocket pocket in plan.RectangularPockets)
                extraRemovedMm3 += pocket.AreaMm2 * pocket.Depth;
            foreach (CircularPocket pocket in plan.CircularPockets)
                extraRemovedMm3 += pocket.AreaMm2 * pocket.Depth;
            foreach (StraightSlot slot in plan.StraightSlots)
                extraRemovedMm3 += slot.AreaMm2 * slot.Depth;
            plan.ExpectedVolumeM3 = plan.ExpectedAfterBossesVolumeM3 - extraRemovedMm3 * 1e-9;
            if (plan.ExpectedVolumeM3 <= 1e-9)
                throw new Fault("INVALID_ARGUMENTS", "The requested pockets and slots remove the entire profile.");
            return plan;
        }

        internal object ToJson()
        {
            object profile;
            if (ProfileType == "rectangle") profile = Json.Obj("type", ProfileType, "width_mm", WidthMm, "height_mm", HeightMm);
            else if (ProfileType == "circle") profile = Json.Obj("type", ProfileType, "diameter_mm", DiameterMm);
            else
            {
                var points = new List<object>(); foreach (PlanPoint point in Points) points.Add(point.ToJson());
                profile = Json.Obj("type", ProfileType, "points_mm", points.ToArray());
            }
            var holes = new List<object>(); foreach (PlanHole hole in Holes) holes.Add(hole.ToJson());
            var rectangular = new List<object>(); foreach (RectangularPocket pocket in RectangularPockets) rectangular.Add(pocket.ToJson());
            var circular = new List<object>(); foreach (CircularPocket pocket in CircularPockets) circular.Add(pocket.ToJson());
            var slots = new List<object>(); foreach (StraightSlot slot in StraightSlots) slots.Add(slot.ToJson());
            var rectangularBosses = new List<object>(); foreach (RectangularBoss boss in RectangularBosses) rectangularBosses.Add(boss.ToJson());
            var circularBosses = new List<object>(); foreach (CircularBoss boss in CircularBosses) circularBosses.Add(boss.ToJson());
            return Json.Obj("plan_version", PlanVersion, "outer_profile", profile, "thickness_mm", ThicknessMm,
                "holes", holes.ToArray(),
                "circular_hole_pattern", Pattern == null ? null : Pattern.ToJson(),
                "rectangular_pockets", rectangular.ToArray(),
                "circular_pockets", circular.ToArray(),
                "straight_slots", slots.ToArray(),
                "rectangular_bosses", rectangularBosses.ToArray(),
                "circular_bosses", circularBosses.ToArray(),
                "properties", Properties == null ? null : Properties.ToJson(),
                "material", MaterialName,
                "calculated", Json.Obj("outer_area_mm2", OuterAreaMm2,
                    "base_volume_after_through_holes_m3", BaseExpectedVolumeM3,
                    "boss_added_volume_m3", BossAddedVolumeM3,
                    "volume_after_bosses_m3", ExpectedAfterBossesVolumeM3,
                    "extra_cut_volume_m3", ExpectedAfterBossesVolumeM3 - ExpectedVolumeM3,
                    "net_volume_m3", ExpectedVolumeM3,
                    "envelope_xyz_mm", new[] { SpanXMm, SpanYMm, ThicknessMm + MaxBossExtrusionMm }));
        }
    }
}
