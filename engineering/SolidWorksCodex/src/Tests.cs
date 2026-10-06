using System;
using System.Collections.Generic;
using System.IO;

namespace SolidWorksLocal
{
    // Explicit offline protocol tests; this fixture is never used by --stdio or --worker.
    internal static class Tests
    {
        static int passed;
        static void Assert(bool condition, string name)
        { if (!condition) throw new Exception("SELF-TEST FAILED: " + name); passed++; }
        static Dictionary<string, object> D(object o) { return Json.Map(o); }
        static string Request(int id, string method, object args)
        { return Json.Encode(Json.Obj("jsonrpc", "2.0", "id", id, "method", method, "params", args)); }
        static object Initialize(Protocol p, string version)
        { return p.Handle(Request(1, "initialize", Json.Obj("protocolVersion", version, "capabilities", Json.Obj(), "clientInfo", Json.Obj("name", "test", "version", "1")))); }
        static object Tool(Protocol p, string name, object a)
        { return p.Handle(Request(8, "tools/call", Json.Obj("name", name, "arguments", a))); }
        static Dictionary<string, object> FlangePlan()
        {
            var holes = new List<object>();
            holes.Add(Json.Obj("x_mm", 0, "y_mm", 0, "diameter_mm", 40));
            for (int i = 0; i < 6; i++)
            {
                double angle = 2.0 * Math.PI * i / 6.0;
                holes.Add(Json.Obj("x_mm", Math.Round(35.0 * Math.Cos(angle), 6),
                    "y_mm", Math.Round(35.0 * Math.Sin(angle), 6), "diameter_mm", 8));
            }
            return Json.Obj("plan_version", "1", "outer_profile", Json.Obj("type", "circle", "diameter_mm", 100),
                "thickness_mm", 10, "holes", holes.ToArray());
        }
        static Dictionary<string, object> ParametricFlangePlan()
        {
            return Json.Obj("plan_version", "2",
                "outer_profile", Json.Obj("type", "circle", "diameter_mm", 220),
                "thickness_mm", 3,
                "circular_hole_pattern", Json.Obj("pitch_circle_diameter_mm", 178,
                    "hole_diameter_mm", 17, "hole_count", 3, "start_angle_deg", 90),
                "properties", Json.Obj("designation", "25.SHT.G.00.00.00.05", "name", "Фланец наружний"),
                "material", "AISI 304");
        }
        static Dictionary<string, object> PocketPlatePlan()
        {
            return Json.Obj("plan_version", "3",
                "outer_profile", Json.Obj("type", "rectangle", "width_mm", 160, "height_mm", 100),
                "thickness_mm", 12,
                "rectangular_pockets", new[] { Json.Obj("x_mm", -45, "y_mm", 22,
                    "width_mm", 36, "height_mm", 22, "depth_mm", 4) },
                "circular_pockets", new[] { Json.Obj("x_mm", 45, "y_mm", 22,
                    "diameter_mm", 24, "depth_mm", 6) },
                "straight_slots", new[] { Json.Obj("x1_mm", -25, "y1_mm", -25,
                    "x2_mm", 25, "y2_mm", -25, "width_mm", 12, "cut_type", "through") },
                "properties", Json.Obj("designation", "AI.TEST.070", "name", "Контрольная плита с карманами"),
                "material", "AISI 304");
        }
        static Dictionary<string, object> SteppedPlatePlan()
        {
            return Json.Obj("plan_version", "4",
                "outer_profile", Json.Obj("type", "rectangle", "width_mm", 180, "height_mm", 110),
                "thickness_mm", 12,
                "rectangular_pockets", new[] { Json.Obj("x_mm", 64, "y_mm", -25,
                    "width_mm", 24, "height_mm", 16, "depth_mm", 4) },
                "circular_pockets", new[] { Json.Obj("x_mm", 0, "y_mm", 25,
                    "diameter_mm", 20, "depth_mm", 5) },
                "straight_slots", new[] { Json.Obj("x1_mm", -35, "y1_mm", -28,
                    "x2_mm", 35, "y2_mm", -28, "width_mm", 12, "cut_type", "through") },
                "rectangular_bosses", new[] { Json.Obj("x_mm", 45, "y_mm", 25,
                    "width_mm", 46, "height_mm", 24, "extrusion_mm", 10) },
                "circular_bosses", new[] { Json.Obj("x_mm", -50, "y_mm", 25,
                    "diameter_mm", 36, "extrusion_mm", 18) },
                "properties", Json.Obj("designation", "AI.TEST.080", "name", "Ступенчатая контрольная плита"),
                "material", "AISI 304");
        }
        static Dictionary<string, object> FinishedBossPlatePlan()
        {
            return Json.Obj("plan_version", "5",
                "outer_profile", Json.Obj("type", "rectangle", "width_mm", 200, "height_mm", 120),
                "thickness_mm", 12,
                "circular_pockets", new[] { Json.Obj("x_mm", 0, "y_mm", -18,
                    "diameter_mm", 20, "depth_mm", 5) },
                "straight_slots", new[] { Json.Obj("x1_mm", -30, "y1_mm", -42,
                    "x2_mm", 30, "y2_mm", -42, "width_mm", 10, "cut_type", "through") },
                "rectangular_bosses", new[] {
                    Json.Obj("x_mm", -55, "y_mm", 25, "width_mm", 54, "height_mm", 34,
                        "extrusion_mm", 12, "corner_style", "chamfer", "corner_size_mm", 5),
                    Json.Obj("x_mm", 55, "y_mm", 25, "width_mm", 54, "height_mm", 34,
                        "extrusion_mm", 16, "corner_style", "round", "corner_size_mm", 7)
                },
                "properties", Json.Obj("designation", "AI.TEST.090", "name", "Плита с фасками и скруглениями"),
                "material", "AISI 304");
        }
        static Dictionary<string, object> FinishedPolygonPlan()
        {
            return Json.Obj("plan_version", "6",
                "outer_profile", Json.Obj("type", "polygon", "points_mm", new[] {
                    Json.Obj("x_mm", -100, "y_mm", -60,
                        "corner_style", "round", "corner_size_mm", 10),
                    Json.Obj("x_mm", 100, "y_mm", -60,
                        "corner_style", "chamfer", "corner_size_mm", 8),
                    Json.Obj("x_mm", 100, "y_mm", 60),
                    Json.Obj("x_mm", -100, "y_mm", 60)
                }),
                "thickness_mm", 5,
                "holes", new[] { Json.Obj("x_mm", 0, "y_mm", 0, "diameter_mm", 12) },
                "properties", Json.Obj("designation", "AI.TEST.100", "name", "Контрольный многоугольник v6"),
                "material", "AISI 304");
        }
        static object Line(double x1, double y1, double x2, double y2)
        { return Json.Obj("type", "line", "start_x_mm", x1, "start_y_mm", y1, "end_x_mm", x2, "end_y_mm", y2); }
        static object Arc(double x1, double y1, double x2, double y2, double cx, double cy, bool clockwise)
        { return Json.Obj("type", "arc", "start_x_mm", x1, "start_y_mm", y1, "end_x_mm", x2, "end_y_mm", y2,
            "center_x_mm", cx, "center_y_mm", cy, "clockwise", clockwise); }
        static Dictionary<string, object> ContourSheetPlan()
        {
            object[] outer = {
                Line(-90, -50, 90, -50), Arc(90, -50, 100, -40, 90, -40, false),
                Line(100, -40, 100, 40), Arc(100, 40, 90, 50, 90, 40, false),
                Line(90, 50, -90, 50), Arc(-90, 50, -100, 40, -90, 40, false),
                Line(-100, 40, -100, -40), Arc(-100, -40, -90, -50, -90, -40, false)
            };
            object[] inner = { Line(-30, -30, 30, -30), Line(30, -30, 30, -10),
                Line(30, -10, -30, -10), Line(-30, -10, -30, -30) };
            return Json.Obj("plan_version", "1", "thickness_mm", 3,
                "outer_contour", Json.Obj("segments", outer),
                "inner_contours", new[] { Json.Obj("segments", inner) },
                "linear_hole_patterns", new[] { Json.Obj("start_x_mm", -60, "start_y_mm", 25,
                    "step_x_mm", 40, "step_y_mm", 0, "count", 4, "diameter_mm", 8) },
                "properties", Json.Obj("designation", "AI.CONTOUR.001", "name", "Контрольный контурный лист"),
                "material", "AISI 304");
        }
        static Dictionary<string, object> ProfileAnglePlan()
        {
            return Json.Obj("plan_version", "1",
                "cross_section", Json.Obj("type", "equal_angle", "leg_a_mm", 40, "leg_b_mm", 40, "thickness_mm", 3),
                "length_mm", 200,
                "hole_groups", new[] {
                    Json.Obj("face", "leg_a", "pattern", "linear", "diameter_mm", 6, "edge_offset_mm", 20,
                        "start_mm", 40, "count", 3, "pitch_mm", 60),
                    Json.Obj("face", "leg_b", "pattern", "explicit", "diameter_mm", 5, "edge_offset_mm", 15,
                        "positions_mm", new object[] { 100.0 }, "count", 1)
                },
                "properties", Json.Obj("designation", "AI_CONTROL_PROFILE_ANGLE_01", "name", "Контрольный уголок"),
                "material", "AISI 304");
        }
        static Dictionary<string, object> RectangularTubePlan()
        {
            return Json.Obj("plan_version", "2",
                "cross_section", Json.Obj("type", "rectangular_tube",
                    "width_mm", 40, "height_mm", 40, "wall_thickness_mm", 4,
                    "outer_corner_radius_mm", 8, "inner_corner_radius_mm", 4),
                "length_mm", 260,
                "hole_groups", new[] {
                    Json.Obj("face", "face_a", "pattern", "explicit",
                        "diameter_mm", 18, "edge_offset_mm", 20,
                        "positions_mm", new object[] { 69.5, 190.5 }, "count", 2)
                },
                "properties", Json.Obj("designation", "AI_CONTROL_RECTANGULAR_TUBE_01", "name", "Контрольная труба"),
                "material", "AISI 304");
        }
        static Dictionary<string, object> RoundTubePlan()
        {
            return Json.Obj("plan_version", "2",
                "cross_section", Json.Obj("type", "round_tube",
                    "outer_diameter_mm", 33.7, "wall_thickness_mm", 3),
                "length_mm", 262,
                "hole_groups", new object[0],
                "properties", Json.Obj("designation", "AI_CONTROL_ROUND_TUBE_01", "name", "Труба"),
                "material", "AISI 304");
        }
        static Dictionary<string, object> SlottedRectangularTubePlan()
        {
            return Json.Obj("plan_version", "3",
                "cross_section", Json.Obj("type", "rectangular_tube",
                    "width_mm", 40, "height_mm", 40, "wall_thickness_mm", 4,
                    "outer_corner_radius_mm", 8, "inner_corner_radius_mm", 4),
                "length_mm", 500,
                "hole_groups", new object[0],
                "slot_groups", new[] {
                    Json.Obj("face", "face_a", "pattern", "explicit",
                        "length_mm", 90, "width_mm", 13, "edge_offset_mm", 20,
                        "positions_mm", new object[] { 100.0, 300.0 }, "count", 2)
                },
                "properties", Json.Obj("designation", "AI_CONTROL_PROFILE_SLOT_01",
                    "name", "Контрольная труба с пазами"),
                "material", "AISI 304");
        }
        static Dictionary<string, object> ChainPinPlan()
        {
            object[] outer = {
                Json.Obj("x_mm", 0, "diameter_mm", 48), Json.Obj("x_mm", 1, "diameter_mm", 50),
                Json.Obj("x_mm", 9, "diameter_mm", 50), Json.Obj("x_mm", 10, "diameter_mm", 48),
                Json.Obj("x_mm", 10, "diameter_mm", 35), Json.Obj("x_mm", 35, "diameter_mm", 35),
                Json.Obj("x_mm", 36, "diameter_mm", 33), Json.Obj("x_mm", 66, "diameter_mm", 33),
                Json.Obj("x_mm", 67, "diameter_mm", 35), Json.Obj("x_mm", 99, "diameter_mm", 35),
                Json.Obj("x_mm", 100, "diameter_mm", 33)
            };
            object[] bore = {
                Json.Obj("x_mm", 46, "diameter_mm", 0), Json.Obj("x_mm", 47.15, "diameter_mm", 4),
                Json.Obj("x_mm", 86.201721, "diameter_mm", 4), Json.Obj("x_mm", 87.553658, "diameter_mm", 8.5),
                Json.Obj("x_mm", 100, "diameter_mm", 8.5)
            };
            return Json.Obj("plan_version", "2", "outer_profile", outer, "axial_bore_profile", bore,
                "radial_holes", new[] { Json.Obj("x_mm", 51, "diameter_mm", 4) },
                "side_flat_slots", new[] { Json.Obj("x_start_mm", 92, "x_end_mm", 95.2,
                    "floor_radius_mm", 14.5, "side", "positive") },
                "reference_volume_mm3", 100957.212334685);
        }
        static Dictionary<string, object> ShaftEndPlan()
        {
            object[] outer = {
                Json.Obj("x_mm", 0, "diameter_mm", 152), Json.Obj("x_mm", 4, "diameter_mm", 160),
                Json.Obj("x_mm", 160, "diameter_mm", 160), Json.Obj("x_mm", 160, "diameter_mm", 172),
                Json.Obj("x_mm", 164.663076582, "diameter_mm", 192), Json.Obj("x_mm", 175, "diameter_mm", 192),
                Json.Obj("x_mm", 179, "diameter_mm", 200), Json.Obj("x_mm", 187, "diameter_mm", 200),
                Json.Obj("x_mm", 187, "diameter_mm", 180), Json.Obj("x_mm", 197, "diameter_mm", 180),
                Json.Obj("x_mm", 197, "diameter_mm", 192), Json.Obj("x_mm", 384, "diameter_mm", 192),
                Json.Obj("x_mm", 390, "diameter_mm", 180), Json.Obj("x_mm", 443, "diameter_mm", 180),
                Json.Obj("x_mm", 443, "diameter_mm", 172), Json.Obj("x_mm", 483, "diameter_mm", 172),
                Json.Obj("x_mm", 483, "diameter_mm", 163.2),
                Json.Obj("x_mm", 483.121792748, "diameter_mm", 161.975413018),
                Json.Obj("x_mm", 483.468629150, "diameter_mm", 160.937258300),
                Json.Obj("x_mm", 483.987706509, "diameter_mm", 160.243585496),
                Json.Obj("x_mm", 484.6, "diameter_mm", 160), Json.Obj("x_mm", 543, "diameter_mm", 160),
                Json.Obj("x_mm", 543, "diameter_mm", 155), Json.Obj("x_mm", 546.4, "diameter_mm", 155),
                Json.Obj("x_mm", 546.4, "diameter_mm", 160), Json.Obj("x_mm", 550, "diameter_mm", 160),
                Json.Obj("x_mm", 560, "diameter_mm", 140)
            };
            return Json.Obj("plan_version", "3", "outer_profile", outer,
                "spline_zone", Json.Obj("start_x_mm", 197, "tip_end_x_mm", 384, "end_x_mm", 390,
                    "root_diameter_mm", 180, "tip_diameter_mm", 192, "tooth_count", 12,
                    "tooth_width_mm", 25, "phase_angle_deg", 0),
                "properties", Json.Obj("designation", "WRM.02.02.00.003", "name", "Конец вала"),
                "reference_volume_mm3", 13312804.679783953);
        }
        internal static int Run()
        {
            passed = 0; int calls = 0;
            Assert(Program.Version == "2.5.0", "connector version");
            Assert(Program.PdmVaultNameMeansBlocked("Engineering"), "named PDM vault path is blocked");
            Assert(!Program.PdmVaultNameMeansBlocked(""), "empty PDM vault result is ordinary local path");
            Assert(SolidWorksReader.PlateDrivingDimensionCount(4) == 15,
                "four-hole plate has fifteen driving dimensions");
            Assert(SolidWorksReader.SameSketchPoint(0.060, -0.040, 0.060, -0.040),
                "rectangle corner coordinates match");
            Assert(!SolidWorksReader.SameSketchPoint(0.060, -0.040, 0.061, -0.040),
                "different rectangle corners do not match");
            var p = new Protocol(delegate(string tool, Dictionary<string, object> args) {
                calls++;
                if (tool == "sw_part") throw new Fault("SELECTION_PRESENT", "Снимите выделение");
                return Json.Obj("fixture", true, "text", "Материал: Сталь 20\nразмер 25 мм", "tool", tool);
            });
            Assert(D(p.Handle("{" )).ContainsKey("error"), "malformed JSON");
            Assert(D(p.Handle("[]")).ContainsKey("error"), "no batch");
            Assert(D(p.Handle("null")).ContainsKey("error"), "null request");
            Assert(D(p.Handle(Request(3, "tools/list", Json.Obj()))).ContainsKey("error"), "pre-init gate");
            Assert(D(p.Handle(Request(1, "initialize", Json.Obj()))).ContainsKey("error"), "invalid initialize");
            var init = D(Json.At(D(Initialize(p, "2099-01-01")), "result"));
            Assert((string)init["protocolVersion"] == "2025-06-18", "protocol negotiation");
            Assert(D(p.Handle(Request(3, "tools/list", Json.Obj()))).ContainsKey("error"), "initialized notification gate");
            Assert(p.Handle("{\"jsonrpc\":\"2.0\",\"method\":\"notifications/initialized\"}") == null, "no notification reply");
            Assert(D(Initialize(p, "2025-06-18")).ContainsKey("error"), "no duplicate initialize");
            Assert(D(p.Handle(Request(3, "ping", Json.Obj()))).ContainsKey("result"), "ping");
            var list = D(Json.At(D(p.Handle(Request(4, "tools/list", Json.Obj()))), "result"));
            Assert(((object[])list["tools"]).Length == 35, "thirty-five tools including scoped experiments and named global variables");
            Assert(calls == 0, "discovery does not connect CAD");
            Assert(SolidWorksReader.TestPathInside(@"C:\Test", @"C:\Test\part.SLDPRT"), "test scope admits a child file");
            Assert(SolidWorksReader.TestPathInside(@"C:\Test\", @"c:\test\child\part.SLDPRT"), "test scope canonical case and trailing separator");
            foreach (string outside in new[] { @"C:\Test2\part.SLDPRT", @"C:\Test\..\part.SLDPRT", @"D:\Test\part.SLDPRT", @"\\server\part.SLDPRT", @"part.SLDPRT", @"C:\Test" })
                Assert(!SolidWorksReader.TestPathInside(@"C:\Test", outside), "test scope rejects " + outside);
            Assert(!SolidWorksReader.TestPathInside(@"C:\", @"C:\part.SLDPRT"), "entire drive cannot be a test scope");
            Assert(D(Tool(p, "sw_test_document", Json.Obj("test_root", @"C:\Test", "file_path", @"C:\Other\part.SLDPRT", "operation", "close"))).ContainsKey("error"), "outside test target rejected before COM");
            Assert(D(Tool(p, "sw_test_document", Json.Obj("test_root", @"C:\Test", "file_path", @"C:\Test\part.SLDPRT", "operation", "macro"))).ContainsKey("error"), "test operation cannot be arbitrary COM");
            Assert(D(Tool(p, "sw_test_document", Json.Obj("test_root", @"C:\Test", "file_path", @"C:\Test\part.SLDPRT", "operation", "close", "force", true))).ContainsKey("error"), "no force close override");
            Assert(calls == 0, "invalid experiment requests never invoke CAD");
            Assert(D(Tool(p, "sw_document", Json.Obj())).ContainsKey("result"), "allowed tool");
            Assert(calls == 1, "one invocation");
            foreach (string forbidden in new[] { "sw_save", "sw_delete", "run_macro", "invoke_com", "execute", "sw_status & whoami" })
                Assert(D(Tool(p, forbidden, Json.Obj())).ContainsKey("error"), "reject " + forbidden);
            Assert(D(Tool(p, "sw_document", Json.Obj("path", "C:\\secret"))).ContainsKey("error"), "no arbitrary read path");
            Assert(D(Tool(p, "sw_export_snapshot", Json.Obj("path", "..\\model.SLDPRT"))).ContainsKey("error"), "no arbitrary export path");
            Assert(D(Tool(p, "sw_export_snapshot", Json.Obj("content", "fake"))).ContainsKey("error"), "no caller report content");
            Assert(D(Tool(p, "sw_status", new object[0])).ContainsKey("error"), "invalid arguments shape");
            Assert(D(Tool(p, "sw_components", Json.Obj("limit", 100000))).ContainsKey("error"), "bounded page");
            Assert(D(Tool(p, "sw_components", Json.Obj("limit", 1.5))).ContainsKey("error"), "integer page");
            Assert(D(Tool(p, "sw_components", Json.Obj("offset", -1))).ContainsKey("error"), "nonnegative offset");
            Assert(D(Tool(p, "sw_components", Json.Obj("limit", "50"))).ContainsKey("error"), "no numeric strings");
            Assert(D(Tool(p, "sw_workspace_status", Json.Obj("limit", 101))).ContainsKey("error"), "bounded workspace listing");
            Assert(D(Tool(p, "sw_open_workspace_file", Json.Obj("file_name", "C:\\outside.SLDPRT"))).ContainsKey("error"), "workspace open rejects path");
            Assert(D(Tool(p, "sw_open_workspace_file", Json.Obj("file_name", "part.SLDASM"))).ContainsKey("error"), "workspace open rejects assembly");
            Assert(D(Tool(p, "sw_open_local_file", Json.Obj("file_path", "\\\\server\\share\\part.SLDPRT"))).ContainsKey("error"), "local open rejects UNC");
            Assert(D(Tool(p, "sw_open_local_file", Json.Obj("file_path", "relative\\part.SLDPRT"))).ContainsKey("error"), "local open requires drive path");
            Assert(D(Tool(p, "sw_open_local_file", Json.Obj("file_path", "C:\\Models\\assembly.SLDASM"))).ContainsKey("error"), "local open rejects assembly");
            Assert(D(Tool(p, "sw_open_assembly_readonly", Json.Obj("file_path", "C:\\Models\\part.SLDPRT"))).ContainsKey("error"), "assembly open rejects non-assembly extension");
            Assert(D(Tool(p, "sw_open_assembly_readonly", Json.Obj("file_path", "\\\\server\\share\\assembly.SLDASM"))).ContainsKey("error"), "assembly open rejects UNC");
            Assert(D(Tool(p, "sw_open_assembly_readonly", Json.Obj("file_path", "relative\\assembly.SLDASM"))).ContainsKey("error"), "assembly open requires drive path");
            Assert(D(Tool(p, "sw_open_assembly_readonly", Json.Obj())).ContainsKey("error"), "assembly open requires file_path");
            Assert(D(Tool(p, "sw_assembly_tree", Json.Obj("limit", 100000))).ContainsKey("error"), "assembly tree page is bounded");
            Assert(D(Tool(p, "sw_assembly_tree", Json.Obj("offset", -1))).ContainsKey("error"), "assembly tree nonnegative offset");
            Assert(D(Tool(p, "sw_equations", Json.Obj("path", "C:\\outside.SLDPRT"))).ContainsKey("error"), "equations reject unexpected argument");
            Assert(D(Tool(p, "sw_configurations", Json.Obj("limit", 5))).ContainsKey("error"), "configurations reject unexpected argument");
            Assert(D(Tool(p, "sw_document_dependencies", Json.Obj())).ContainsKey("error"), "dependencies require file_path");
            Assert(D(Tool(p, "sw_document_dependencies", Json.Obj("file_path", "C:\\Models\\assembly.txt"))).ContainsKey("error"), "dependencies reject unsupported extension");
            Assert(D(Tool(p, "sw_document_dependencies", Json.Obj("file_path", "\\\\server\\share\\assembly.SLDASM"))).ContainsKey("error"), "dependencies reject UNC");
            Assert(D(Tool(p, "sw_document_dependencies", Json.Obj("file_path", "relative\\assembly.SLDASM"))).ContainsKey("error"), "dependencies require drive path");
            Assert(D(Tool(p, "sw_document_dependencies", Json.Obj("file_path", "C:\\Models\\assembly.SLDASM", "limit", 5))).ContainsKey("error"), "dependencies reject unexpected argument");
            Assert(D(Tool(p, "sw_component_details", Json.Obj())).ContainsKey("error"), "component details require instance_id");
            Assert(D(Tool(p, "sw_component_details", Json.Obj("instance_id", ""))).ContainsKey("error"), "component details reject empty instance_id");
            Assert(D(Tool(p, "sw_component_details", Json.Obj("instance_id", "Part1-1", "limit", 5))).ContainsKey("error"), "component details reject unexpected argument");
            Assert(D(Tool(p, "sw_component_details", Json.Obj("instance_id", new string('x', 2049)))).ContainsKey("error"), "component details reject oversize instance_id");
            Assert(D(Tool(p, "sw_create_drawing", Json.Obj("projection", "unknown"))).ContainsKey("error"), "drawing rejects unknown projection");
            Assert(D(Tool(p, "sw_create_drawing", Json.Obj("dimensions", "invent"))).ContainsKey("error"), "drawing rejects invented dimensions mode");
            Assert(D(Tool(p, "sw_export_workspace_pdf", Json.Obj("path", "C:\\outside.pdf"))).ContainsKey("error"), "PDF export rejects caller path");
            Assert(D(Tool(p, "sw_set_parameter", Json.Obj())).ContainsKey("error"), "parameter change requires identity and values");
            Assert(D(Tool(p, "sw_set_parameter", Json.Obj("full_name", "AI_Length@Sketch1", "expected_current_mm", 120, "new_value_mm", 120))).ContainsKey("error"), "parameter change rejects unchanged value");
            Assert(D(Tool(p, "sw_set_parameter", Json.Obj("full_name", "AI_Length@Sketch1", "expected_current_mm", 120, "new_value_mm", 140, "path", "C:\\outside.SLDPRT"))).ContainsKey("error"), "parameter change rejects caller path");
            Assert(D(Tool(p, "sw_set_parameters", Json.Obj())).ContainsKey("error"), "parameter group requires changes");
            Assert(D(Tool(p, "sw_features", Json.Obj("limit", 101))).ContainsKey("error"), "feature inventory is bounded");
            Assert(D(Tool(p, "sw_set_feature_dimensions", Json.Obj())).ContainsKey("error"), "feature edit requires exact identity and changes");
            Assert(D(Tool(p, "sw_set_feature_dimensions", Json.Obj("feature_name", "Boss-Extrude1", "expected_feature_type", "Sketch", "changes", new[] {
                Json.Obj("full_name", "D1@Boss-Extrude1@Part1.SLDPRT", "expected_current_mm", 5, "new_value_mm", 8)
            }))).ContainsKey("error"), "feature edit rejects unsupported feature type");
            Assert(D(Tool(p, "sw_set_global_variable", Json.Obj())).ContainsKey("error"), "global variable requires exact identity, dimension and name");
            Assert(D(Tool(p, "sw_set_global_variable", Json.Obj("feature_name", "Boss-Extrude1", "expected_feature_type", "Sketch",
                "full_name", "D1@Boss-Extrude1@Part1.SLDPRT", "expected_current_mm", 208, "value_mm", 208, "variable_name", "crossbar_length_mm"))).ContainsKey("error"),
                "global variable rejects unsupported feature type");
            Assert(D(Tool(p, "sw_set_global_variable", Json.Obj("feature_name", "Boss-Extrude1", "expected_feature_type", "Extrusion",
                "full_name", "D1@Boss-Extrude1@Part1.SLDPRT", "expected_current_mm", 208, "value_mm", 228.8, "variable_name", "1crossbar"))).ContainsKey("error"),
                "global variable rejects a name starting with a digit");
            Assert(D(Tool(p, "sw_set_global_variable", Json.Obj("feature_name", "Boss-Extrude1", "expected_feature_type", "Extrusion",
                "full_name", "D1@Boss-Extrude1@Part1.SLDPRT", "expected_current_mm", 208, "value_mm", 228.8, "variable_name", "crossbar length"))).ContainsKey("error"),
                "global variable rejects a name containing a space");
            Assert(D(Tool(p, "sw_set_global_variable", Json.Obj("feature_name", "Boss-Extrude1", "expected_feature_type", "Extrusion",
                "full_name", "D1@Boss-Extrude1@Part1.SLDPRT", "expected_current_mm", 208, "value_mm", 228.8, "variable_name", "crossbar_length_mm", "path", "C:\\outside.SLDPRT"))).ContainsKey("error"),
                "global variable rejects unexpected argument");
            Assert(D(Tool(p, "sw_set_parameters", Json.Obj("changes", new[] {
                Json.Obj("full_name", "AI_Length@Sketch1", "expected_current_mm", 120, "new_value_mm", 140),
                Json.Obj("full_name", "AI_Length@Sketch1", "expected_current_mm", 120, "new_value_mm", 150)
            }))).ContainsKey("error"), "parameter group rejects duplicate identity");
            Assert(D(Tool(p, "sw_set_parameters", Json.Obj("changes", new[] {
                Json.Obj("full_name", "AI_Length@Sketch1", "expected_current_mm", 120, "new_value_mm", 140, "path", "C:\\outside.SLDPRT")
            }))).ContainsKey("error"), "parameter group rejects item fields");
            Assert(D(Tool(p, "sw_create_parameter_variant", Json.Obj("source_path", "\\\\server\\share\\outside.SLDPRT", "changes", new[] {
                Json.Obj("full_name", "AI_Length@Sketch1", "expected_current_mm", 120, "new_value_mm", 140)
            }))).ContainsKey("error"), "parameter variant rejects network source path");
            Assert(D(Tool(p, "sw_create_parameter_variant", Json.Obj("source_file_name", "drawing.SLDDRW", "changes", new[] {
                Json.Obj("full_name", "AI_Length@Sketch1", "expected_current_mm", 120, "new_value_mm", 140)
            }))).ContainsKey("error"), "parameter variant requires source SLDPRT");
            Assert(D(Tool(p, "sw_create_parameter_variant", Json.Obj("source_file_name", "part.SLDPRT", "source_path", "C:\\Models\\part.SLDPRT", "changes", new[] {
                Json.Obj("full_name", "AI_Length@Sketch1", "expected_current_mm", 120, "new_value_mm", 140)
            }))).ContainsKey("error"), "parameter variant rejects two source selectors");
            Assert(D(Tool(p, "sw_create_parameter_variant", Json.Obj("changes", new[] {
                Json.Obj("full_name", "AI_Length@Sketch1", "expected_current_mm", 120, "new_value_mm", 140)
            }))).ContainsKey("error"), "parameter variant requires one source selector");
            Assert(D(Tool(p, "sw_set_workspace_properties", Json.Obj())).ContainsKey("error"), "workspace properties require a value");
            Assert(D(Tool(p, "sw_set_workspace_properties", Json.Obj("material", "Steel"))).ContainsKey("error"), "workspace properties reject unverified material");
            Assert(D(Tool(p, "sw_set_workspace_properties", Json.Obj("name", "bad\nname"))).ContainsKey("error"), "workspace properties reject controls");
            Assert(D(Tool(p, "sw_create_plate", Json.Obj())).ContainsKey("error"), "plate requires dimensions");
            Assert(D(Tool(p, "sw_create_plate", Json.Obj("length_mm", 100, "width_mm", 60, "thickness_mm", 5,
                "hole_diameter_mm", 8, "edge_offset_x_mm", 10, "edge_offset_y_mm", 10, "path", "C:\\model.SLDPRT"))).ContainsKey("error"), "plate rejects path");
            Assert(D(Tool(p, "sw_create_plate", Json.Obj("length_mm", 100, "width_mm", 60, "thickness_mm", 5,
                "hole_diameter_mm", 8, "edge_offset_x_mm", 49, "edge_offset_y_mm", 10))).ContainsKey("error"), "plate holes fit inside");
            Assert(D(Tool(p, "sw_create_part_from_plan", Json.Obj())).ContainsKey("error"), "part plan requires version and profile");
            Assert(D(Tool(p, "sw_create_sheet_from_contours", Json.Obj())).ContainsKey("error"), "sheet contour requires version, thickness and outer contour");
            ContourPartPlan contour = ContourPartPlan.Parse(ContourSheetPlan());
            Assert(contour.Outer.Segments.Count == 8 && contour.Inner.Count == 1 && contour.Holes.Count == 4,
                "sheet contour lines arcs cutout and expanded linear pattern");
            Assert(Math.Abs(contour.SpanXMm - 200.0) < 0.01 && Math.Abs(contour.SpanYMm - 100.0) < 0.01,
                "sheet contour analytic envelope");
            Assert(contour.ExpectedVolumeM3 > 0.0, "sheet contour positive analytic volume");
            var openContour = ContourSheetPlan();
            var openOuter = D(openContour["outer_contour"]); var openSegments = (object[])openOuter["segments"];
            var badLast = D(openSegments[openSegments.Length - 1]); badLast["end_x_mm"] = -89;
            Assert(D(Tool(p, "sw_create_sheet_from_contours", openContour)).ContainsKey("error"), "sheet contour rejects open loop");
            Assert(D(Tool(p, "sw_create_part_from_plan", Json.Obj("plan_version", "1", "outer_profile",
                Json.Obj("type", "circle", "diameter_mm", 100), "thickness_mm", 10, "path", "C:\\model.SLDPRT"))).ContainsKey("error"), "part plan rejects path");
            Assert(D(Tool(p, "sw_create_part_from_plan", Json.Obj("plan_version", "1", "outer_profile",
                Json.Obj("type", "circle", "diameter_mm", 100), "thickness_mm", 10,
                "holes", new[] { Json.Obj("x_mm", 49, "y_mm", 0, "diameter_mm", 8) }))).ContainsKey("error"), "part plan rejects outside hole");
            Assert(D(Tool(p, "sw_create_part_from_plan", Json.Obj("plan_version", "1", "outer_profile",
                Json.Obj("type", "rectangle", "width_mm", 100, "height_mm", 60), "thickness_mm", 5,
                "holes", new[] { Json.Obj("x_mm", 0, "y_mm", 0, "diameter_mm", 10),
                    Json.Obj("x_mm", 5, "y_mm", 0, "diameter_mm", 10) }))).ContainsKey("error"), "part plan rejects overlapping holes");
            Assert(D(Tool(p, "sw_create_part_from_plan", Json.Obj("plan_version", "1", "outer_profile",
                Json.Obj("type", "polygon", "points_mm", new[] { Json.Obj("x_mm", -10, "y_mm", -10),
                    Json.Obj("x_mm", 10, "y_mm", 10), Json.Obj("x_mm", -10, "y_mm", 10),
                    Json.Obj("x_mm", 10, "y_mm", -10) }), "thickness_mm", 5))).ContainsKey("error"), "part plan rejects self-intersecting polygon");
            Assert(D(Tool(p, "sw_create_part_from_plan", Json.Obj("plan_version", "1", "outer_profile",
                Json.Obj("type", "circle", "diameter_mm", 100), "thickness_mm", 10,
                "material", "AISI 304"))).ContainsKey("error"), "part plan v1 rejects v2 material field");
            var unsupportedMaterial = ParametricFlangePlan(); unsupportedMaterial["material"] = "Steel";
            Assert(D(Tool(p, "sw_create_part_from_plan", unsupportedMaterial)).ContainsKey("error"), "part plan rejects unsupported material");
            Assert(D(Tool(p, "sw_create_part_from_plan", Json.Obj("plan_version", "2", "outer_profile",
                Json.Obj("type", "circle", "diameter_mm", 100), "thickness_mm", 10,
                "circular_hole_pattern", Json.Obj("pitch_circle_diameter_mm", 96,
                    "hole_diameter_mm", 8, "hole_count", 3, "start_angle_deg", 90)))).ContainsKey("error"),
                "circular pattern must fit outer profile");
            Assert(D(Tool(p, "sw_create_part_from_plan", Json.Obj("plan_version", "2", "outer_profile",
                Json.Obj("type", "circle", "diameter_mm", 100), "thickness_mm", 10,
                "circular_hole_pattern", Json.Obj("pitch_circle_diameter_mm", 10,
                    "hole_diameter_mm", 8, "hole_count", 6, "start_angle_deg", 0)))).ContainsKey("error"),
                "circular pattern holes do not overlap");
            var badPrismaticProperty = ParametricFlangePlan();
            badPrismaticProperty["properties"] = Json.Obj("name", "Фланец\nRUN");
            Assert(D(Tool(p, "sw_create_part_from_plan", badPrismaticProperty)).ContainsKey("error"),
                "prismatic properties reject controls");
            Assert(D(Tool(p, "sw_create_part_from_plan", Json.Obj("plan_version", "2", "outer_profile",
                Json.Obj("type", "rectangle", "width_mm", 100, "height_mm", 60), "thickness_mm", 10,
                "rectangular_pockets", new[] { Json.Obj("x_mm", 0, "y_mm", 0, "width_mm", 20,
                    "height_mm", 10, "depth_mm", 3) }))).ContainsKey("error"), "prismatic v2 rejects v3 cuts");
            Assert(D(Tool(p, "sw_create_part_from_plan", Json.Obj("plan_version", "3", "outer_profile",
                Json.Obj("type", "polygon", "points_mm", new[] { Json.Obj("x_mm", -30, "y_mm", -20),
                    Json.Obj("x_mm", 30, "y_mm", -20), Json.Obj("x_mm", 30, "y_mm", 20),
                    Json.Obj("x_mm", -30, "y_mm", 20) }), "thickness_mm", 10,
                "circular_pockets", new[] { Json.Obj("x_mm", 0, "y_mm", 0, "diameter_mm", 10,
                    "depth_mm", 3) }))).ContainsKey("error"), "prismatic v3 cuts reject polygon base");
            Assert(D(Tool(p, "sw_create_part_from_plan", Json.Obj("plan_version", "3", "outer_profile",
                Json.Obj("type", "rectangle", "width_mm", 100, "height_mm", 60), "thickness_mm", 10,
                "straight_slots", new[] { Json.Obj("x1_mm", -20, "y1_mm", 0, "x2_mm", 20,
                    "y2_mm", 0, "width_mm", 8, "cut_type", "through", "depth_mm", 10) }))).ContainsKey("error"),
                "through slot rejects depth");
            Assert(D(Tool(p, "sw_create_part_from_plan", Json.Obj("plan_version", "3", "outer_profile",
                Json.Obj("type", "rectangle", "width_mm", 100, "height_mm", 60), "thickness_mm", 10,
                "straight_slots", new[] { Json.Obj("x1_mm", -20, "y1_mm", 0, "x2_mm", 20,
                    "y2_mm", 0, "width_mm", 8, "cut_type", "blind") }))).ContainsKey("error"),
                "blind slot requires depth");
            Assert(D(Tool(p, "sw_create_part_from_plan", Json.Obj("plan_version", "3", "outer_profile",
                Json.Obj("type", "rectangle", "width_mm", 100, "height_mm", 60), "thickness_mm", 10,
                "straight_slots", new[] { Json.Obj("x1_mm", -2, "y1_mm", 0, "x2_mm", 2,
                    "y2_mm", 0, "width_mm", 8, "cut_type", "through") }))).ContainsKey("error"),
                "slot arc centres fit width rule");
            Assert(D(Tool(p, "sw_create_part_from_plan", Json.Obj("plan_version", "3", "outer_profile",
                Json.Obj("type", "circle", "diameter_mm", 100), "thickness_mm", 10,
                "rectangular_pockets", new[] { Json.Obj("x_mm", 40, "y_mm", 0, "width_mm", 30,
                    "height_mm", 20, "depth_mm", 3) }))).ContainsKey("error"), "pocket fits outer profile");
            Assert(D(Tool(p, "sw_create_part_from_plan", Json.Obj("plan_version", "3", "outer_profile",
                Json.Obj("type", "rectangle", "width_mm", 100, "height_mm", 60), "thickness_mm", 10,
                "holes", new[] { Json.Obj("x_mm", 0, "y_mm", 0, "diameter_mm", 10) },
                "circular_pockets", new[] { Json.Obj("x_mm", 7, "y_mm", 0, "diameter_mm", 10,
                    "depth_mm", 3) }))).ContainsKey("error"), "cuts reject hole overlap");
            Assert(D(Tool(p, "sw_create_part_from_plan", Json.Obj("plan_version", "3", "outer_profile",
                Json.Obj("type", "rectangle", "width_mm", 100, "height_mm", 60), "thickness_mm", 10,
                "circular_bosses", new[] { Json.Obj("x_mm", 0, "y_mm", 0, "diameter_mm", 20,
                    "extrusion_mm", 5) }))).ContainsKey("error"), "prismatic v3 rejects v4 bosses");
            Assert(D(Tool(p, "sw_create_part_from_plan", Json.Obj("plan_version", "4", "outer_profile",
                Json.Obj("type", "polygon", "points_mm", new[] { Json.Obj("x_mm", -30, "y_mm", -20),
                    Json.Obj("x_mm", 30, "y_mm", -20), Json.Obj("x_mm", 30, "y_mm", 20),
                    Json.Obj("x_mm", -30, "y_mm", 20) }), "thickness_mm", 10,
                "rectangular_bosses", new[] { Json.Obj("x_mm", 0, "y_mm", 0, "width_mm", 20,
                    "height_mm", 10, "extrusion_mm", 5) }))).ContainsKey("error"),
                "prismatic v4 bosses reject polygon base");
            Assert(D(Tool(p, "sw_create_part_from_plan", Json.Obj("plan_version", "4", "outer_profile",
                Json.Obj("type", "circle", "diameter_mm", 100), "thickness_mm", 10,
                "circular_bosses", new[] { Json.Obj("x_mm", 45, "y_mm", 0, "diameter_mm", 20,
                    "extrusion_mm", 5) }))).ContainsKey("error"), "boss fits outer profile");
            Assert(D(Tool(p, "sw_create_part_from_plan", Json.Obj("plan_version", "4", "outer_profile",
                Json.Obj("type", "rectangle", "width_mm", 100, "height_mm", 60), "thickness_mm", 10,
                "rectangular_pockets", new[] { Json.Obj("x_mm", 0, "y_mm", 0, "width_mm", 20,
                    "height_mm", 10, "depth_mm", 3) },
                "circular_bosses", new[] { Json.Obj("x_mm", 0, "y_mm", 0, "diameter_mm", 8,
                    "extrusion_mm", 5) }))).ContainsKey("error"), "bosses reject cut overlap");
            Assert(D(Tool(p, "sw_create_part_from_plan", Json.Obj("plan_version", "4", "outer_profile",
                Json.Obj("type", "rectangle", "width_mm", 100, "height_mm", 60), "thickness_mm", 10,
                "rectangular_bosses", new[] { Json.Obj("x_mm", 0, "y_mm", 0, "width_mm", 20,
                    "height_mm", 10, "extrusion_mm", 5) },
                "circular_bosses", new[] { Json.Obj("x_mm", 8, "y_mm", 0, "diameter_mm", 10,
                    "extrusion_mm", 5) }))).ContainsKey("error"), "bosses reject each other overlap");
            Assert(D(Tool(p, "sw_create_part_from_plan", Json.Obj("plan_version", "4", "outer_profile",
                Json.Obj("type", "rectangle", "width_mm", 100, "height_mm", 60), "thickness_mm", 10,
                "rectangular_bosses", new[] { Json.Obj("x_mm", 0, "y_mm", 0, "width_mm", 20,
                    "height_mm", 10, "extrusion_mm", 5, "corner_style", "round", "corner_size_mm", 2) }))).ContainsKey("error"),
                "prismatic v4 rejects v5 corner finish");
            Assert(D(Tool(p, "sw_create_part_from_plan", Json.Obj("plan_version", "5", "outer_profile",
                Json.Obj("type", "rectangle", "width_mm", 100, "height_mm", 60), "thickness_mm", 10,
                "rectangular_bosses", new[] { Json.Obj("x_mm", 0, "y_mm", 0, "width_mm", 20,
                    "height_mm", 10, "extrusion_mm", 5, "corner_style", "round") }))).ContainsKey("error"),
                "v5 corner style requires size");
            Assert(D(Tool(p, "sw_create_part_from_plan", Json.Obj("plan_version", "5", "outer_profile",
                Json.Obj("type", "rectangle", "width_mm", 100, "height_mm", 60), "thickness_mm", 10,
                "rectangular_bosses", new[] { Json.Obj("x_mm", 0, "y_mm", 0, "width_mm", 20,
                    "height_mm", 10, "extrusion_mm", 5, "corner_size_mm", 2) }))).ContainsKey("error"),
                "v5 corner size requires style");
            Assert(D(Tool(p, "sw_create_part_from_plan", Json.Obj("plan_version", "5", "outer_profile",
                Json.Obj("type", "rectangle", "width_mm", 100, "height_mm", 60), "thickness_mm", 10,
                "rectangular_bosses", new[] { Json.Obj("x_mm", 0, "y_mm", 0, "width_mm", 20,
                    "height_mm", 10, "extrusion_mm", 5, "corner_style", "bevel", "corner_size_mm", 2) }))).ContainsKey("error"),
                "v5 rejects unknown corner style");
            Assert(D(Tool(p, "sw_create_part_from_plan", Json.Obj("plan_version", "5", "outer_profile",
                Json.Obj("type", "rectangle", "width_mm", 100, "height_mm", 60), "thickness_mm", 10,
                "rectangular_bosses", new[] { Json.Obj("x_mm", 0, "y_mm", 0, "width_mm", 20,
                    "height_mm", 10, "extrusion_mm", 5, "corner_style", "chamfer", "corner_size_mm", 5) }))).ContainsKey("error"),
                "v5 corner finish fits rectangular boss");
            Assert(D(Tool(p, "sw_create_turned_part_from_plan", Json.Obj())).ContainsKey("error"), "turned plan requires profile");
            Assert(D(Tool(p, "sw_create_turned_part_from_plan", Json.Obj("plan_version", "3", "outer_profile", new[] {
                Json.Obj("x_mm", 0, "diameter_mm", 20), Json.Obj("x_mm", 20, "diameter_mm", 20) }))).ContainsKey("error"), "turned v3 requires spline zone");
            var pathPlan = ChainPinPlan(); pathPlan.Add("path", "C:\\model.SLDPRT");
            Assert(D(Tool(p, "sw_create_turned_part_from_plan", pathPlan)).ContainsKey("error"), "turned plan rejects path");
            Assert(D(Tool(p, "sw_create_turned_part_from_plan", Json.Obj("plan_version", "2", "outer_profile", new[] {
                Json.Obj("x_mm", 0, "diameter_mm", 20), Json.Obj("x_mm", 20, "diameter_mm", 20),
                Json.Obj("x_mm", 10, "diameter_mm", 15) }))).ContainsKey("error"), "turned profile x is monotonic");
            Assert(D(Tool(p, "sw_create_turned_part_from_plan", Json.Obj("plan_version", "2", "outer_profile", new[] {
                Json.Obj("x_mm", 0, "diameter_mm", 20), Json.Obj("x_mm", 20, "diameter_mm", 20) },
                "axial_bore_profile", new[] { Json.Obj("x_mm", 5, "diameter_mm", 2),
                    Json.Obj("x_mm", 20, "diameter_mm", 4) }))).ContainsKey("error"), "turned bore must start at zero diameter");
            Assert(D(Tool(p, "sw_create_turned_part_from_plan", Json.Obj("plan_version", "2", "outer_profile", new[] {
                Json.Obj("x_mm", 0, "diameter_mm", 20), Json.Obj("x_mm", 20, "diameter_mm", 20) },
                "radial_holes", new[] { Json.Obj("x_mm", 10, "diameter_mm", 20) }))).ContainsKey("error"), "radial hole fits local diameter");
            Assert(D(Tool(p, "sw_create_turned_part_from_plan", Json.Obj("plan_version", "2", "outer_profile", new[] {
                Json.Obj("x_mm", 0, "diameter_mm", 20), Json.Obj("x_mm", 20, "diameter_mm", 20) },
                "radial_holes", new[] { Json.Obj("x_mm", 10, "diameter_mm", 4),
                    Json.Obj("x_mm", 12, "diameter_mm", 4) }))).ContainsKey("error"), "radial holes do not overlap");
            Assert(D(Tool(p, "sw_create_turned_part_from_plan", Json.Obj("plan_version", "2", "outer_profile", new[] {
                Json.Obj("x_mm", 0, "diameter_mm", 20), Json.Obj("x_mm", 20, "diameter_mm", 20) },
                "side_flat_slots", new[] { Json.Obj("x_start_mm", 5, "x_end_mm", 8,
                    "floor_radius_mm", 10, "side", "positive") }))).ContainsKey("error"), "side slot must remove material");
            Assert(D(Tool(p, "sw_create_turned_part_from_plan", Json.Obj("plan_version", "2", "outer_profile", new[] {
                Json.Obj("x_mm", 0, "diameter_mm", 20), Json.Obj("x_mm", 20, "diameter_mm", 20) },
                "reference_volume_mm3", 1000000))).ContainsKey("error"), "reference cannot exceed revolved body");
            var v2Spline = ChainPinPlan(); v2Spline.Add("spline_zone", Json.Obj());
            Assert(D(Tool(p, "sw_create_turned_part_from_plan", v2Spline)).ContainsKey("error"), "turned v2 rejects spline zone");
            var wideTooth = ShaftEndPlan();
            wideTooth["spline_zone"] = Json.Obj("start_x_mm", 197, "tip_end_x_mm", 384, "end_x_mm", 390,
                "root_diameter_mm", 180, "tip_diameter_mm", 192, "tooth_count", 12,
                "tooth_width_mm", 50, "phase_angle_deg", 0);
            Assert(D(Tool(p, "sw_create_turned_part_from_plan", wideTooth)).ContainsKey("error"), "spline tooth fits pitch");
            var badEnvelope = ShaftEndPlan();
            badEnvelope["spline_zone"] = Json.Obj("start_x_mm", 197, "tip_end_x_mm", 384, "end_x_mm", 390,
                "root_diameter_mm", 180, "tip_diameter_mm", 190, "tooth_count", 12,
                "tooth_width_mm", 25, "phase_angle_deg", 0);
            Assert(D(Tool(p, "sw_create_turned_part_from_plan", badEnvelope)).ContainsKey("error"), "spline matches envelope");
            var badProperty = ShaftEndPlan();
            badProperty["properties"] = Json.Obj("designation", "WRM\nRUN");
            Assert(D(Tool(p, "sw_create_turned_part_from_plan", badProperty)).ContainsKey("error"), "new part properties reject controls");
            ProfilePartPlan angle = ProfilePartPlan.Parse(ProfileAnglePlan());
            Assert(angle.LegAMm == 40 && angle.LegBMm == 40 && angle.ThicknessMm == 3 && angle.LengthMm == 200,
                "profile plan reads equal-angle cross-section and length");
            Assert(angle.Holes.Count == 4, "profile plan expands linear and explicit hole groups (3+1)");
            Assert(angle.ExpectedVolumeM3 > 0.0, "profile plan positive analytic volume");
            ProfilePartPlan rectangularTube = ProfilePartPlan.Parse(RectangularTubePlan());
            Assert(rectangularTube.IsRectangularTube && rectangularTube.WidthMm == 40 &&
                rectangularTube.HeightMm == 40 && rectangularTube.ThicknessMm == 4,
                "profile plan v2 reads rectangular tube cross-section");
            Assert(rectangularTube.Holes.Count == 2 &&
                rectangularTube.Holes[0].WallCount == 2,
                "rectangular tube holes are explicitly counted through both opposite walls");
            double rectangularOuterArea = 40 * 40 - (4.0 - Math.PI) * 8 * 8;
            double rectangularInnerArea = 32 * 32 - (4.0 - Math.PI) * 4 * 4;
            double rectangularExpectedVolume = ((rectangularOuterArea - rectangularInnerArea) * 260 -
                2 * Math.PI * 9 * 9 * 4 * 2) * 1e-9;
            Assert(Math.Abs(rectangularTube.ExpectedVolumeM3 - rectangularExpectedVolume) < 1e-15,
                "rectangular tube analytic volume includes rounded section and both-wall cuts");
            ProfilePartPlan roundProfile = ProfilePartPlan.Parse(RoundTubePlan());
            double roundExpectedArea = Math.PI * (33.7 * 33.7 - 27.7 * 27.7) / 4.0;
            Assert(roundProfile.IsRoundTube && Math.Abs(roundProfile.InnerDiameterMm - 27.7) < 1e-12,
                "profile plan v2 derives round tube inner diameter");
            Assert(Math.Abs(roundProfile.ExpectedVolumeM3 - roundExpectedArea * 262 * 1e-9) < 1e-15,
                "round tube analytic volume");
            ProfilePartPlan slottedTube = ProfilePartPlan.Parse(SlottedRectangularTubePlan());
            double slotArea = (90.0 - 13.0) * 13.0 + Math.PI * 6.5 * 6.5;
            double slottedExpectedVolume = ((rectangularOuterArea - rectangularInnerArea) * 500.0 -
                2.0 * slotArea * 4.0 * 2.0) * 1e-9;
            Assert(slottedTube.Slots.Count == 2 && slottedTube.Slots[0].WallCount == 2,
                "profile plan v3 expands rectangular-tube slots through both walls");
            Assert(Math.Abs(slottedTube.ExpectedVolumeM3 - slottedExpectedVolume) < 1e-15,
                "profile slot analytic volume includes straight centre and circular caps");
            Assert(D(Tool(p, "sw_create_profile_part_from_plan", Json.Obj())).ContainsKey("error"), "profile plan requires version, cross_section and length");
            var profilePathPlan = ProfileAnglePlan(); profilePathPlan.Add("path", "C:\\model.SLDPRT");
            Assert(D(Tool(p, "sw_create_profile_part_from_plan", profilePathPlan)).ContainsKey("error"), "profile plan rejects path");
            var roundTube = ProfileAnglePlan();
            roundTube["cross_section"] = Json.Obj("type", "round_tube", "leg_a_mm", 40, "leg_b_mm", 40, "thickness_mm", 3);
            Assert(D(Tool(p, "sw_create_profile_part_from_plan", roundTube)).ContainsKey("error"), "profile plan v1 rejects tube cross-sections");
            var badTubeRadii = RectangularTubePlan();
            badTubeRadii["cross_section"] = Json.Obj("type", "rectangular_tube",
                "width_mm", 40, "height_mm", 40, "wall_thickness_mm", 4,
                "outer_corner_radius_mm", 8, "inner_corner_radius_mm", 2);
            Assert(D(Tool(p, "sw_create_profile_part_from_plan", badTubeRadii)).ContainsKey("error"),
                "rectangular tube rejects non-constant-wall corner radii");
            var roundTubeWithHole = RoundTubePlan();
            roundTubeWithHole["hole_groups"] = new[] {
                Json.Obj("face", "face_a", "pattern", "explicit", "diameter_mm", 6,
                    "edge_offset_mm", 10, "positions_mm", new object[] { 100.0 }, "count", 1)
            };
            Assert(D(Tool(p, "sw_create_profile_part_from_plan", roundTubeWithHole)).ContainsKey("error"),
                "round tube rejects side holes without a circumferential datum");
            var v2WithSlots = RectangularTubePlan();
            v2WithSlots["slot_groups"] = new[] {
                Json.Obj("face", "face_a", "pattern", "explicit", "length_mm", 20,
                    "width_mm", 6, "edge_offset_mm", 20,
                    "positions_mm", new object[] { 100.0 }, "count", 1)
            };
            Assert(D(Tool(p, "sw_create_profile_part_from_plan", v2WithSlots)).ContainsKey("error"),
                "profile slot groups require plan v3");
            var roundTubeWithSlot = RoundTubePlan();
            roundTubeWithSlot["plan_version"] = "3";
            roundTubeWithSlot["slot_groups"] = new[] {
                Json.Obj("face", "face_a", "pattern", "explicit", "length_mm", 20,
                    "width_mm", 6, "edge_offset_mm", 10,
                    "positions_mm", new object[] { 100.0 }, "count", 1)
            };
            Assert(D(Tool(p, "sw_create_profile_part_from_plan", roundTubeWithSlot)).ContainsKey("error"),
                "round tube rejects slots without a circumferential datum");
            var invalidSlotShape = SlottedRectangularTubePlan();
            invalidSlotShape["slot_groups"] = new[] {
                Json.Obj("face", "face_a", "pattern", "explicit", "length_mm", 10,
                    "width_mm", 10, "edge_offset_mm", 20,
                    "positions_mm", new object[] { 100.0 }, "count", 1)
            };
            Assert(D(Tool(p, "sw_create_profile_part_from_plan", invalidSlotShape)).ContainsKey("error"),
                "profile slot requires a nonzero straight section");
            var overlappingSlots = SlottedRectangularTubePlan();
            overlappingSlots["slot_groups"] = new[] {
                Json.Obj("face", "face_a", "pattern", "explicit", "length_mm", 90,
                    "width_mm", 13, "edge_offset_mm", 20,
                    "positions_mm", new object[] { 100.0, 150.0 }, "count", 2)
            };
            Assert(D(Tool(p, "sw_create_profile_part_from_plan", overlappingSlots)).ContainsKey("error"),
                "profile slots cannot overlap on one face");
            var badRectangularFace = RectangularTubePlan();
            badRectangularFace["hole_groups"] = new[] {
                Json.Obj("face", "leg_a", "pattern", "explicit", "diameter_mm", 6,
                    "edge_offset_mm", 20, "positions_mm", new object[] { 100.0 }, "count", 1)
            };
            Assert(D(Tool(p, "sw_create_profile_part_from_plan", badRectangularFace)).ContainsKey("error"),
                "rectangular tube requires face_a or face_b");
            var crossingTubeHoles = RectangularTubePlan();
            crossingTubeHoles["hole_groups"] = new[] {
                Json.Obj("face", "face_a", "pattern", "explicit", "diameter_mm", 6,
                    "edge_offset_mm", 20, "positions_mm", new object[] { 100.0 }, "count", 1),
                Json.Obj("face", "face_b", "pattern", "explicit", "diameter_mm", 6,
                    "edge_offset_mm", 20, "positions_mm", new object[] { 100.0 }, "count", 1)
            };
            Assert(D(Tool(p, "sw_create_profile_part_from_plan", crossingTubeHoles)).ContainsKey("error"),
                "rectangular tube rejects intersecting perpendicular hole cylinders");
            var degenerateTubeRadius = RectangularTubePlan();
            degenerateTubeRadius["cross_section"] = Json.Obj("type", "rectangular_tube",
                "width_mm", 40, "height_mm", 40, "wall_thickness_mm", 4,
                "outer_corner_radius_mm", 20, "inner_corner_radius_mm", 16);
            Assert(D(Tool(p, "sw_create_profile_part_from_plan", degenerateTubeRadius)).ContainsKey("error"),
                "rectangular tube rejects a corner radius that removes every straight edge");
            var tooThick = ProfileAnglePlan();
            tooThick["cross_section"] = Json.Obj("type", "equal_angle", "leg_a_mm", 10, "leg_b_mm", 40, "thickness_mm", 9.5);
            Assert(D(Tool(p, "sw_create_profile_part_from_plan", tooThick)).ContainsKey("error"), "profile plan thickness must leave leg material beyond the corner");
            var badMaterial = ProfileAnglePlan(); badMaterial["material"] = "Steel";
            Assert(D(Tool(p, "sw_create_profile_part_from_plan", badMaterial)).ContainsKey("error"), "profile plan rejects unverified material");
            var overlapping = ProfileAnglePlan();
            overlapping["hole_groups"] = new[] {
                Json.Obj("face", "leg_a", "pattern", "explicit", "diameter_mm", 6, "edge_offset_mm", 20,
                    "positions_mm", new object[] { 40.0, 44.0 }, "count", 2)
            };
            Assert(D(Tool(p, "sw_create_profile_part_from_plan", overlapping)).ContainsKey("error"), "profile plan rejects overlapping holes on the same leg");
            var outsideLength = ProfileAnglePlan();
            outsideLength["hole_groups"] = new[] {
                Json.Obj("face", "leg_a", "pattern", "explicit", "diameter_mm", 6, "edge_offset_mm", 20,
                    "positions_mm", new object[] { 198.0 }, "count", 1)
            };
            Assert(D(Tool(p, "sw_create_profile_part_from_plan", outsideLength)).ContainsKey("error"), "profile plan rejects a hole too close to the part end");
            var offLeg = ProfileAnglePlan();
            offLeg["hole_groups"] = new[] {
                Json.Obj("face", "leg_a", "pattern", "explicit", "diameter_mm", 6, "edge_offset_mm", 39,
                    "positions_mm", new object[] { 100.0 }, "count", 1)
            };
            Assert(D(Tool(p, "sw_create_profile_part_from_plan", offLeg)).ContainsKey("error"), "profile plan rejects a hole too close to the leg edge");
            var countMismatch = ProfileAnglePlan();
            countMismatch["hole_groups"] = new[] {
                Json.Obj("face", "leg_a", "pattern", "explicit", "diameter_mm", 6, "edge_offset_mm", 20,
                    "positions_mm", new object[] { 40.0, 100.0 }, "count", 1)
            };
            Assert(D(Tool(p, "sw_create_profile_part_from_plan", countMismatch)).ContainsKey("error"), "profile plan explicit count must equal positions_mm length");
            var tightPitch = ProfileAnglePlan();
            tightPitch["hole_groups"] = new[] {
                Json.Obj("face", "leg_a", "pattern", "linear", "diameter_mm", 6, "edge_offset_mm", 20,
                    "start_mm", 40, "count", 3, "pitch_mm", 5)
            };
            Assert(D(Tool(p, "sw_create_profile_part_from_plan", tightPitch)).ContainsKey("error"), "profile plan linear pitch must exceed hole diameter");
            var badFace = ProfileAnglePlan();
            badFace["hole_groups"] = new[] {
                Json.Obj("face", "leg_c", "pattern", "explicit", "diameter_mm", 6, "edge_offset_mm", 20,
                    "positions_mm", new object[] { 100.0 }, "count", 1)
            };
            Assert(D(Tool(p, "sw_create_profile_part_from_plan", badFace)).ContainsKey("error"), "profile plan face must be leg_a or leg_b");
            var badVersion = ProfileAnglePlan(); badVersion["plan_version"] = "4";
            Assert(D(Tool(p, "sw_create_profile_part_from_plan", badVersion)).ContainsKey("error"), "profile plan rejects unknown plan_version");
            PartPlan flange = PartPlan.Parse(FlangePlan());
            Assert(flange.ProfileType == "circle" && flange.Holes.Count == 7, "flange plan parses");
            double expectedFlangeVolume = (Math.PI * 50 * 50 - Math.PI * 20 * 20 - 6 * Math.PI * 4 * 4) * 10 * 1e-9;
            Assert(Math.Abs(flange.ExpectedVolumeM3 - expectedFlangeVolume) < 1e-15, "flange plan volume");
            PartPlan parametricFlange = PartPlan.Parse(ParametricFlangePlan());
            Assert(parametricFlange.PlanVersion == "2" && parametricFlange.Pattern != null &&
                parametricFlange.Holes.Count == 3, "parametric flange plan parses");
            Assert(Math.Abs(parametricFlange.Holes[0].X) < 1e-12 &&
                Math.Abs(parametricFlange.Holes[0].Y - 89) < 1e-12, "parametric flange top hole");
            Assert(Math.Abs(parametricFlange.Holes[1].X + 77.0762609368150) < 1e-9 &&
                Math.Abs(parametricFlange.Holes[1].Y + 44.5) < 1e-9 &&
                Math.Abs(parametricFlange.Holes[2].X - 77.0762609368150) < 1e-9 &&
                Math.Abs(parametricFlange.Holes[2].Y + 44.5) < 1e-9, "parametric flange lower holes");
            double expectedParametricVolume = (Math.PI * 110 * 110 - 3 * Math.PI * 8.5 * 8.5) * 3 * 1e-9;
            Assert(Math.Abs(parametricFlange.ExpectedVolumeM3 - expectedParametricVolume) < 1e-15,
                "parametric flange volume");
            Assert(parametricFlange.Properties != null &&
                parametricFlange.Properties.Designation == "25.SHT.G.00.00.00.05" &&
                parametricFlange.Properties.Name == "Фланец наружний", "parametric flange properties");
            Assert(parametricFlange.MaterialName == "AISI 304", "parametric flange material");
            PartPlan pocketPlate = PartPlan.Parse(PocketPlatePlan());
            Assert(pocketPlate.PlanVersion == "3" && pocketPlate.RectangularPockets.Count == 1 &&
                pocketPlate.CircularPockets.Count == 1 && pocketPlate.StraightSlots.Count == 1,
                "pocket plate plan parses all v3 cuts");
            Assert(Math.Abs(pocketPlate.BaseExpectedVolumeM3 - 192000e-9) < 1e-15,
                "pocket plate base volume");
            double expectedSlotArea = 50 * 12 + Math.PI * 6 * 6;
            double expectedPocketPlateVolume = (192000 - 36 * 22 * 4 - Math.PI * 12 * 12 * 6 -
                expectedSlotArea * 12) * 1e-9;
            Assert(Math.Abs(pocketPlate.StraightSlots[0].LengthMm - 50) < 1e-12 &&
                Math.Abs(pocketPlate.StraightSlots[0].AreaMm2 - expectedSlotArea) < 1e-12,
                "straight slot dimensions and area");
            Assert(Math.Abs(pocketPlate.ExpectedVolumeM3 - expectedPocketPlateVolume) < 1e-15,
                "pocket plate final volume");
            Assert(pocketPlate.Properties != null && pocketPlate.Properties.Designation == "AI.TEST.070" &&
                pocketPlate.MaterialName == "AISI 304", "pocket plate properties and material");
            PartPlan steppedPlate = PartPlan.Parse(SteppedPlatePlan());
            Assert(steppedPlate.PlanVersion == "4" && steppedPlate.RectangularBosses.Count == 1 &&
                steppedPlate.CircularBosses.Count == 1 && steppedPlate.RectangularPockets.Count == 1 &&
                steppedPlate.CircularPockets.Count == 1 && steppedPlate.StraightSlots.Count == 1,
                "stepped plate parses v4 bosses and v3 cuts");
            double expectedBossVolume = (46 * 24 * 10 + Math.PI * 18 * 18 * 18) * 1e-9;
            Assert(Math.Abs(steppedPlate.BaseExpectedVolumeM3 - 237600e-9) < 1e-15 &&
                Math.Abs(steppedPlate.BossAddedVolumeM3 - expectedBossVolume) < 1e-15,
                "stepped plate base and boss volumes");
            double expectedSteppedSlotArea = 70 * 12 + Math.PI * 6 * 6;
            double expectedSteppedVolume = 237600e-9 + expectedBossVolume -
                (24 * 16 * 4 + Math.PI * 10 * 10 * 5 + expectedSteppedSlotArea * 12) * 1e-9;
            Assert(Math.Abs(steppedPlate.ExpectedAfterBossesVolumeM3 - (237600e-9 + expectedBossVolume)) < 1e-15 &&
                Math.Abs(steppedPlate.ExpectedVolumeM3 - expectedSteppedVolume) < 1e-15,
                "stepped plate after-boss and final volumes");
            Assert(Math.Abs(steppedPlate.MaxBossExtrusionMm - 18) < 1e-12 &&
                steppedPlate.Properties.Designation == "AI.TEST.080" && steppedPlate.MaterialName == "AISI 304",
                "stepped plate envelope property and material inputs");
            PartPlan finishedPlate = PartPlan.Parse(FinishedBossPlatePlan());
            Assert(finishedPlate.PlanVersion == "5" && finishedPlate.RectangularBosses.Count == 2 &&
                finishedPlate.RectangularBosses[0].CornerStyle == "chamfer" &&
                finishedPlate.RectangularBosses[1].CornerStyle == "round",
                "finished plate parses v5 chamfer and round styles");
            double chamferedArea = 54 * 34 - 2 * 5 * 5;
            double roundedArea = 54 * 34 - (4 - Math.PI) * 7 * 7;
            double expectedFinishedBossVolume = (chamferedArea * 12 + roundedArea * 16) * 1e-9;
            Assert(Math.Abs(finishedPlate.RectangularBosses[0].AreaMm2 - chamferedArea) < 1e-12 &&
                Math.Abs(finishedPlate.RectangularBosses[1].AreaMm2 - roundedArea) < 1e-12,
                "v5 exact chamfered and rounded boss areas");
            Assert(Math.Abs(finishedPlate.BossAddedVolumeM3 - expectedFinishedBossVolume) < 1e-15,
                "v5 finished boss volume");
            double expectedFinishedSlotArea = 60 * 10 + Math.PI * 5 * 5;
            double expectedFinishedVolume = 288000e-9 + expectedFinishedBossVolume -
                (Math.PI * 10 * 10 * 5 + expectedFinishedSlotArea * 12) * 1e-9;
            Assert(Math.Abs(finishedPlate.ExpectedVolumeM3 - expectedFinishedVolume) < 1e-15 &&
                Math.Abs(finishedPlate.MaxBossExtrusionMm - 16) < 1e-12,
                "v5 final volume and envelope height");
            PartPlan finishedPolygon = PartPlan.Parse(FinishedPolygonPlan());
            double expectedFinishedPolygonArea = 200 * 120 - 100 * (1.0 - Math.PI / 4.0) - 32;
            double expectedFinishedPolygonVolume =
                (expectedFinishedPolygonArea - Math.PI * 6 * 6) * 5 * 1e-9;
            Assert(finishedPolygon.PlanVersion == "6" && finishedPolygon.Points.Count == 4 &&
                finishedPolygon.Points[0].CornerStyle == "round" &&
                finishedPolygon.Points[1].CornerStyle == "chamfer", "v6 polygon corner styles parse");
            Assert(Math.Abs(finishedPolygon.OuterAreaMm2 - expectedFinishedPolygonArea) < 1e-9 &&
                Math.Abs(finishedPolygon.ExpectedVolumeM3 - expectedFinishedPolygonVolume) < 1e-15,
                "v6 polygon finished area and volume");
            var clippedCornerHole = FinishedPolygonPlan();
            clippedCornerHole["holes"] = new[] { Json.Obj("x_mm", -98.5, "y_mm", -58.5, "diameter_mm", 1) };
            Assert(D(Tool(p, "sw_create_part_from_plan", clippedCornerHole)).ContainsKey("error"),
                "v6 rejects a hole inside removed rounded-corner material");
            var oversizedCorner = FinishedPolygonPlan();
            oversizedCorner["outer_profile"] = Json.Obj("type", "polygon", "points_mm", new[] {
                Json.Obj("x_mm", 0, "y_mm", 0, "corner_style", "round", "corner_size_mm", 80),
                Json.Obj("x_mm", 100, "y_mm", 0), Json.Obj("x_mm", 100, "y_mm", 50),
                Json.Obj("x_mm", 0, "y_mm", 50) });
            Assert(D(Tool(p, "sw_create_part_from_plan", oversizedCorner)).ContainsKey("error"),
                "v6 rejects corner finishing that consumes an edge");
            Assert(SolidWorksReader.CylinderRadiiMatch(new[] { 7.0, 10.0, 5.0, 7.0, 7.0, 5.0, 7.0 }, null,
                new[] { 7.0, 7.0, 7.0, 7.0, 10.0, 5.0, 5.0 }),
                "analytic radii include four rounded corners, pocket and slot ends");
            Assert(SolidWorksReader.CylinderRadiiMatch(new[] { 6.0, 18.0, 10.0, 6.0 }, null,
                new[] { 18.0, 10.0, 6.0, 6.0 }), "analytic radii include circular boss, pocket and slot ends");
            Assert(SolidWorksReader.CylinderRadiiMatch(new[] { 8.5, 110.0, 8.5, 8.5 }, 110.0,
                new[] { 8.5, 8.5, 8.5 }), "analytic cylinder radii accept order-independent exact flange");
            Assert(SolidWorksReader.CylinderRadiiMatch(new[] { 8.5005, 109.9999, 8.4995, 8.5 }, 110.0,
                new[] { 8.5, 8.5, 8.5 }), "analytic cylinder radii accept sub-micron noise");
            Assert(!SolidWorksReader.CylinderRadiiMatch(new[] { 8.5, 8.5, 8.5 }, 110.0,
                new[] { 8.5, 8.5, 8.5 }), "analytic cylinder radii reject missing outer circle");
            Assert(!SolidWorksReader.CylinderRadiiMatch(new[] { 8.5, 8.5, 8.5, 109.0 }, 110.0,
                new[] { 8.5, 8.5, 8.5 }), "analytic cylinder radii reject wrong outer diameter");
            TurnedPartPlan pin = TurnedPartPlan.Parse(ChainPinPlan());
            Assert(pin.Outer.Count == 11 && pin.Bore.Count == 5 && pin.RadialHoles.Count == 1 && pin.SideSlots.Count == 1,
                "chain pin turned plan parses");
            Assert(Math.Abs(pin.AxisymmetricVolumeM3 - 101458.807723376e-9) < 1e-12, "chain pin axisymmetric volume");
            Assert(pin.ReferenceVolumeM3.HasValue && Math.Abs(pin.ReferenceVolumeM3.Value - 100957.212334685e-9) < 1e-12,
                "chain pin reference volume");
            TurnedPartPlan shaft = TurnedPartPlan.Parse(ShaftEndPlan());
            Assert(shaft.PlanVersion == "3" && shaft.Spline != null && shaft.Spline.ToothCount == 12,
                "shaft end spline plan parses");
            Assert(Math.Abs(shaft.Spline.RootDiameter - 180) < 1e-12 && Math.Abs(shaft.Spline.TipDiameter - 192) < 1e-12,
                "shaft end spline diameters");
            Assert(shaft.Properties != null && shaft.Properties.Designation == "WRM.02.02.00.003" && shaft.Properties.Name == "Конец вала",
                "shaft end safe properties");
            Assert(shaft.ReferenceVolumeM3.HasValue && Math.Abs(shaft.ReferenceVolumeM3.Value - 0.013312804679783953) < 1e-12,
                "shaft end reference volume");
            Assert(calls == 1, "invalid requests never execute");
            Assert(p.Handle("{\"jsonrpc\":\"2.0\",\"method\":\"tools/call\",\"params\":{\"name\":\"sw_export_snapshot\"}}") == null, "tools notification ignored");
            Assert(calls == 1, "notification cannot execute writes");
            var created = D(Json.At(D(Tool(p, "sw_create_plate", Json.Obj("length_mm", 100, "width_mm", 60, "thickness_mm", 5,
                "hole_diameter_mm", 8, "edge_offset_x_mm", 10, "edge_offset_y_mm", 10))), "result"));
            Assert(Object.Equals(created["isError"], false), "valid plate tool call");
            Assert(calls == 2, "validated plate executes once");
            var planned = D(Json.At(D(Tool(p, "sw_create_part_from_plan", FlangePlan())), "result"));
            Assert(Object.Equals(planned["isError"], false), "valid part plan tool call");
            Assert(calls == 3, "validated part plan executes once");
            var parameterized = D(Json.At(D(Tool(p, "sw_create_part_from_plan", ParametricFlangePlan())), "result"));
            Assert(Object.Equals(parameterized["isError"], false), "valid parametric flange tool call");
            Assert(calls == 4, "validated parametric flange executes once");
            var pocketed = D(Json.At(D(Tool(p, "sw_create_part_from_plan", PocketPlatePlan())), "result"));
            Assert(Object.Equals(pocketed["isError"], false), "valid pocket plate tool call");
            Assert(calls == 5, "validated pocket plate executes once");
            var stepped = D(Json.At(D(Tool(p, "sw_create_part_from_plan", SteppedPlatePlan())), "result"));
            Assert(Object.Equals(stepped["isError"], false), "valid stepped plate tool call");
            Assert(calls == 6, "validated stepped plate executes once");
            var finished = D(Json.At(D(Tool(p, "sw_create_part_from_plan", FinishedBossPlatePlan())), "result"));
            Assert(Object.Equals(finished["isError"], false), "valid v5 finished-boss plate tool call");
            Assert(calls == 7, "validated v5 finished-boss plate executes once");
            var turned = D(Json.At(D(Tool(p, "sw_create_turned_part_from_plan", ChainPinPlan())), "result"));
            Assert(Object.Equals(turned["isError"], false), "valid turned plan tool call");
            Assert(calls == 8, "validated turned plan executes once");
            var splined = D(Json.At(D(Tool(p, "sw_create_turned_part_from_plan", ShaftEndPlan())), "result"));
            Assert(Object.Equals(splined["isError"], false), "valid splined shaft plan tool call");
            Assert(calls == 9, "validated splined shaft plan executes once");
            Assert(Object.Equals(D(Json.At(D(Tool(p, "sw_workspace_status", Json.Obj("limit", 25))), "result"))["isError"], false), "workspace status dispatch");
            Assert(Object.Equals(D(Json.At(D(Tool(p, "sw_copy_active_to_workspace", Json.Obj())), "result"))["isError"], false), "workspace copy dispatch");
            Assert(Object.Equals(D(Json.At(D(Tool(p, "sw_open_workspace_file", Json.Obj("file_name", "part.SLDPRT"))), "result"))["isError"], false), "workspace open dispatch");
            Assert(Object.Equals(D(Json.At(D(Tool(p, "sw_open_local_file", Json.Obj("file_path", "C:\\Models\\part.SLDPRT"))), "result"))["isError"], false), "local fixed-disk open dispatch");
            Assert(Object.Equals(D(Json.At(D(Tool(p, "sw_save_workspace_document", Json.Obj())), "result"))["isError"], false), "workspace save dispatch");
            Assert(Object.Equals(D(Json.At(D(Tool(p, "sw_set_workspace_properties", Json.Obj("designation", "TEST.001", "name", "Test part", "material", "AISI 304"))), "result"))["isError"], false), "workspace properties dispatch");
            Assert(Object.Equals(D(Json.At(D(Tool(p, "sw_create_drawing", Json.Obj("projection", "first_angle", "dimensions", "model"))), "result"))["isError"], false), "drawing dispatch");
            Assert(Object.Equals(D(Json.At(D(Tool(p, "sw_drawing", Json.Obj())), "result"))["isError"], false), "drawing audit dispatch");
            Assert(Object.Equals(D(Json.At(D(Tool(p, "sw_export_workspace_pdf", Json.Obj())), "result"))["isError"], false), "PDF export dispatch");
            Assert(SolidWorksReader.IsPdfHeader(new byte[] { 0x25, 0x50, 0x44, 0x46, 0x2D }), "PDF header accepted");
            Assert(!SolidWorksReader.IsPdfHeader(new byte[] { 0x50, 0x44, 0x46 }), "invalid PDF header rejected");
            Assert(SolidWorksReader.IsConnectorParameterName("AI_Length"), "connector parameter prefix accepted");
            Assert(!SolidWorksReader.IsConnectorParameterName("D1"), "ordinary model dimension is not connector-managed");
            Assert(SolidWorksReader.EditableFeatureType("Boss"), "boss feature type accepted for guarded edit");
            Assert(SolidWorksReader.EditableFeatureType("Extrusion"), "SOLIDWORKS 2026 extrusion feature type accepted for guarded edit");
            Assert(SolidWorksReader.EditableFeatureType("Cut"), "cut feature type accepted for guarded edit");
            Assert(!SolidWorksReader.EditableFeatureType("Sketch"), "sketch feature type rejected for guarded edit");
            Assert(SolidWorksReader.LinearDimensionTypeName("swDimensionParamTypeDoubleLinear"), "linear parameter type accepted");
            Assert(!SolidWorksReader.LinearDimensionTypeName("swDimensionParamTypeDoubleAngular"), "angular parameter type rejected");
            Assert(!SolidWorksReader.LinearDimensionTypeName("swDimensionParamTypeInteger"), "integer parameter is not a length");
            Assert(!SolidWorksReader.LinearDimensionTypeName("swDimensionParamTypeUnknown"), "unknown parameter type is not inferred from a name");
            Assert(!SolidWorksReader.LinearDimensionTypeName("swLinearDimension"), "display dimension enum is not a parameter enum");
            double[] ccwArcMiddle = SolidWorksReader.ArcMidpointMetres(0.0, 0.0,
                0.010, 0.0, 0.0, Math.PI / 2.0);
            Assert(Math.Abs(ccwArcMiddle[0] - Math.Sqrt(0.00005)) < 1e-12 &&
                Math.Abs(ccwArcMiddle[1] - Math.Sqrt(0.00005)) < 1e-12,
                "counter-clockwise arc midpoint follows requested quarter sweep");
            double[] cwArcMiddle = SolidWorksReader.ArcMidpointMetres(0.0, 0.0,
                0.0, 0.010, Math.PI / 2.0, -Math.PI / 2.0);
            Assert(Math.Abs(cwArcMiddle[0] - Math.Sqrt(0.00005)) < 1e-12 &&
                Math.Abs(cwArcMiddle[1] - Math.Sqrt(0.00005)) < 1e-12,
                "clockwise arc midpoint follows requested quarter sweep");
            Assert(Program.IsNetworkOrDevicePathText("\\\\server\\share\\part.SLDPRT"), "UNC path text rejected");
            Assert(Program.IsNetworkOrDevicePathText("//server/share/part.SLDPRT"), "forward-slash network path text rejected");
            Assert(!Program.IsNetworkOrDevicePathText("C:\\Models\\part.SLDPRT"), "drive path text is not UNC");
            Assert(Program.IsWritableLocalDriveType(DriveType.Fixed), "fixed drive type accepted for write");
            Assert(!Program.IsWritableLocalDriveType(DriveType.Network), "network drive type rejected for write");
            Assert(!Program.IsWritableLocalDriveType(DriveType.Removable), "removable drive type rejected for write");
            Assert(Object.Equals(D(Json.At(D(Tool(p, "sw_parameters", Json.Obj())), "result"))["isError"], false), "parameter list dispatch");
            Assert(Object.Equals(D(Json.At(D(Tool(p, "sw_features", Json.Obj("offset", 0, "limit", 25))), "result"))["isError"], false), "feature inventory dispatch");
            Assert(Object.Equals(D(Json.At(D(Tool(p, "sw_set_feature_dimensions", Json.Obj("feature_name", "Boss-Extrude1", "expected_feature_type", "Boss", "changes", new[] {
                Json.Obj("full_name", "D1@Boss-Extrude1@Part1.SLDPRT", "expected_current_mm", 5, "new_value_mm", 8)
            }))), "result"))["isError"], false), "guarded feature dimension edit dispatch");
            Assert(Object.Equals(D(Json.At(D(Tool(p, "sw_set_feature_dimensions", Json.Obj("feature_name", "Boss-Extrude1", "expected_feature_type", "Extrusion", "changes", new[] {
                Json.Obj("full_name", "D1@Boss-Extrude1@Part1.SLDPRT", "expected_current_mm", 4, "new_value_mm", 5)
            }))), "result"))["isError"], false), "native extrusion edit dispatch");
            Assert(Object.Equals(D(Json.At(D(Tool(p, "sw_set_parameter", Json.Obj("full_name", "AI_Length@Sketch1@Part1.SLDPRT", "expected_current_mm", 120, "new_value_mm", 140))), "result"))["isError"], false), "parameter change dispatch");
            Assert(Object.Equals(D(Json.At(D(Tool(p, "sw_set_parameters", Json.Obj("changes", new[] {
                Json.Obj("full_name", "AI_Length@Sketch1@Part1.SLDPRT", "expected_current_mm", 120, "new_value_mm", 140),
                Json.Obj("full_name", "AI_Width@Sketch1@Part1.SLDPRT", "expected_current_mm", 80, "new_value_mm", 90)
            }))), "result"))["isError"], false), "parameter group dispatch");
            Assert(Object.Equals(D(Json.At(D(Tool(p, "sw_create_parameter_variant", Json.Obj("source_file_name", "part.SLDPRT", "changes", new[] {
                Json.Obj("full_name", "AI_Length@Sketch1@Part1.SLDPRT", "expected_current_mm", 120, "new_value_mm", 160)
            }))), "result"))["isError"], false), "parameter variant dispatch");
            Assert(Object.Equals(D(Json.At(D(Tool(p, "sw_create_parameter_variant", Json.Obj("source_path", "D:\\Models\\part.SLDPRT", "changes", new[] {
                Json.Obj("full_name", "AI_Width@Sketch1@Part1.SLDPRT", "expected_current_mm", 80, "new_value_mm", 100)
            }))), "result"))["isError"], false), "local-path parameter variant dispatch");
            Assert(calls == 26, "all validated local operations execute");
            var fail = D(Json.At(D(Tool(p, "sw_part", Json.Obj())), "result"));
            Assert(Object.Equals(fail["isError"], true), "tool error flag");
            string unicode = Json.Encode(Json.Obj("text", "Сталь\n\"кавычки\"", "unknown", null));
            Assert((string)D(Json.Decode(unicode))["text"] == "Сталь\n\"кавычки\"", "UTF-8 round trip");
            var input = new StringReader(new string('x', 66000) + "\n" + Request(3, "ping", Json.Obj()) + "\n");
            var output = new StringWriter();
            p.Run(input, output);
            string[] lines = output.ToString().Trim().Split('\n');
            Assert(lines.Length == 2, "oversize recovery");
            Assert(D(Json.Decode(lines[1])).ContainsKey("result"), "server lives after bad request");
            Assert(D(p.Handle(Request(3, "unknown/method", Json.Obj()))).ContainsKey("error"), "unknown method");
            foreach (string supported in new[] { "2024-11-05", "2025-03-26", "2025-06-18" })
            {
                var protocol = new Protocol(delegate { return null; });
                var result = D(Json.At(D(Initialize(protocol, supported)), "result"));
                Assert((string)result["protocolVersion"] == supported, "supported " + supported);
            }
            Assert(Program.WorkerTimeoutMilliseconds("sw_document") == 45000, "read timeout includes mutex wait");
            Assert(Program.WorkerTimeoutMilliseconds("sw_set_feature_dimensions") == 75000, "feature edits receive full write timeout plus mutex wait");
            Assert(Program.WorkerTimeoutMilliseconds("sw_set_global_variable") == 75000, "global variable edits receive full write timeout plus mutex wait");
            Assert(Program.WorkerTimeoutMilliseconds("sw_open_assembly_readonly") == 75000, "assembly open has a bounded load budget");
            Assert(Program.WorkerTimeoutMilliseconds("sw_create_parameter_variant") < 90000, "worker timeout stays under MCP timeout");
            Console.WriteLine("PASS: " + passed + " offline protocol assertions. Live SOLIDWORKS COM is NOT tested by this command.");
            return 0;
        }
    }
}
