using System;
using System.Collections;
using System.Collections.Generic;
using System.Diagnostics;
using System.Globalization;
using System.IO;
using System.Reflection;
using System.Runtime.InteropServices;
using System.Security.Cryptography;
using System.Text;
using System.Threading;

namespace SolidWorksLocal
{
    // Runtime-loaded official Interop interfaces preserve typed COM invocation,
    // especially IModelDoc2.GetType(), which must not call System.Object.GetType().
    internal sealed partial class SolidWorksReader
    {
        Assembly interop, swconst;
        object app, model;
        string revision, path, title, config, token;
        int kind;
        bool? dirty;
        readonly List<object> issues = new List<object>();
        readonly List<object> refs = new List<object>();
        string interopPath, installDir;
        internal int SolidWorksProcessId = -1;

        [DllImport("ole32.dll", CharSet = CharSet.Unicode, PreserveSig = false)]
        static extern void CLSIDFromProgID(string progId, out Guid clsid);
        [DllImport("oleaut32.dll", PreserveSig = false)]
        static extern void GetActiveObject(ref Guid clsid, IntPtr reserved, [MarshalAs(UnmanagedType.IUnknown)] out object value);

        // Every COM-mutating (and COM-reading) operation goes through this single named
        // mutex so that two SolidWorksLocal.exe worker processes -- whether spawned by the
        // same --stdio server, two different --stdio servers (e.g. two concurrent Codex/
        // Claude sessions), or a manual --worker test script -- can never touch the live
        // SOLIDWORKS COM instance at the same time. This does not start a second SOLIDWORKS
        // (Connect() only ever attaches via GetActiveObject, never CreateObject/Process.Start)
        // and it never kills SOLIDWORKS, Codex or the caller: on contention it simply waits a
        // bounded time and, if the mutex is still held, fails fast with CONNECTOR_BUSY. There
        // is no automatic retry anywhere in this path.
        const string ComMutexNameGlobal = "Global\\SolidWorksCodex_COM_Mutex";
        const string ComMutexNameLocal = "Local\\SolidWorksCodex_COM_Mutex";
        internal const int ComMutexTimeoutMs = 20000;

        static Mutex OpenComMutex()
        {
            try { return new Mutex(false, ComMutexNameGlobal); }
            catch (UnauthorizedAccessException) { return new Mutex(false, ComMutexNameLocal); }
            catch (IOException) { return new Mutex(false, ComMutexNameLocal); }
        }

        internal static object Read(string tool, Dictionary<string, object> args)
        {
            Catalog.Validate(tool, args);
            string requestId = Guid.NewGuid().ToString("N");
            int workerPid = Process.GetCurrentProcess().Id;
            DateTime startUtc = DateTime.UtcNow;
            var reader = new SolidWorksReader();
            Mutex mutex = null;
            bool owned = false;
            try
            {
                mutex = OpenComMutex();
                try { owned = mutex.WaitOne(ComMutexTimeoutMs); }
                catch (AbandonedMutexException)
                {
                    // A previous worker process died while holding the mutex. .NET still
                    // grants ownership to this waiter; the mutex itself is not corrupted.
                    owned = true;
                }
                if (!owned)
                {
                    ConnectorCallLog.Write(requestId, workerPid, -1, tool, startUtc, DateTime.UtcNow, "CONNECTOR_BUSY");
                    throw new Fault("CONNECTOR_BUSY",
                        "Коннектор занят другой COM-операцией более " + (ComMutexTimeoutMs / 1000) +
                        " с. Запрос не выполнен и не повторяется автоматически. SOLIDWORKS и другие процессы не были закрыты; повторите запрос вручную позже.");
                }
                try
                {
                    object result = reader.Execute(tool, args);
                    ConnectorCallLog.Write(requestId, workerPid, reader.SolidWorksProcessId, tool, startUtc, DateTime.UtcNow, "OK");
                    return result;
                }
                catch (Fault fault)
                {
                    ConnectorCallLog.Write(requestId, workerPid, reader.SolidWorksProcessId, tool, startUtc, DateTime.UtcNow, "FAULT:" + fault.Code);
                    throw;
                }
                catch (Exception)
                {
                    ConnectorCallLog.Write(requestId, workerPid, reader.SolidWorksProcessId, tool, startUtc, DateTime.UtcNow, "EXCEPTION");
                    throw;
                }
            }
            finally
            {
                // References are confined to a short-lived worker. Do not call Quit,
                // close documents or FinalReleaseComObject on application-owned objects.
                reader.refs.Clear();
                if (owned) { try { mutex.ReleaseMutex(); } catch { } }
                if (mutex != null) mutex.Dispose();
            }
        }
        object Track(object value)
        {
            if (value != null && Marshal.IsComObject(value)) refs.Add(value);
            return value;
        }
        Type Face(string name)
        {
            var type = interop.GetType("SolidWorks.Interop.sldworks." + name, false);
            if (type == null) throw new Fault("API_INTERFACE_MISSING", "Interface not found: " + name);
            return type;
        }
        object Get(object target, string face, string member, params object[] indexes)
        {
            var property = Face(face).GetProperty(member);
            if (property == null) throw new Fault("API_PROPERTY_MISSING", face + "." + member);
            return Track(property.GetValue(target, indexes.Length == 0 ? null : indexes));
        }
        void Set(object target, string face, string member, object value)
        {
            var property = Face(face).GetProperty(member);
            if (property == null) throw new Fault("API_PROPERTY_MISSING", face + "." + member);
            property.SetValue(target, value, null);
        }
        object Call(object target, string face, string method, params object[] args)
        {
            var member = Face(face).GetMethod(method);
            if (member == null) throw new Fault("API_METHOD_MISSING", face + "." + method);
            try
            {
                return Track(member.Invoke(target, args));
            }
            catch (TargetParameterCountException)
            {
                var parameters = member.GetParameters();
                throw new Fault("API_METHOD_PARAMETER_MISMATCH",
                    face + "." + method + " expects " + parameters.Length + " parameter(s) (" +
                    string.Join(", ", Array.ConvertAll(parameters, p => p.ParameterType.Name + " " + p.Name)) +
                    ") but " + args.Length + " were provided.");
            }
        }
        int EnumValue(string typeName, string valueName)
        {
            if (swconst == null) throw new Fault("SWCONST_NOT_FOUND", "SolidWorks.Interop.swconst.dll is required for CAD creation.");
            var type = swconst.GetType("SolidWorks.Interop.swconst." + typeName, false);
            if (type == null || !type.IsEnum) throw new Fault("API_ENUM_MISSING", typeName);
            try { return Convert.ToInt32(Enum.Parse(type, valueName)); }
            catch { throw new Fault("API_ENUM_VALUE_MISSING", typeName + "." + valueName); }
        }
        object Try(string field, Func<object> read)
        {
            try { return read(); }
            catch (Exception ex) { issues.Add(Json.Obj("field", field, "status", "UNKNOWN", "error", Program.Unwrap(ex))); return null; }
        }
        static string Text(object value) { return value == null ? null : Convert.ToString(value, CultureInfo.InvariantCulture); }
        static bool? Bool(object value) { return value == null ? (bool?)null : Convert.ToBoolean(value); }
        object Field(object value, string method, string status = "VERIFIED", string unit = null)
        {
            if (value == null || (value is string && string.IsNullOrWhiteSpace((string)value))) { value = null; status = "UNKNOWN"; }
            return Json.Obj("value", value, "status", status, "unit", unit,
                "source", Json.Obj("api", method, "document", path, "configuration", config, "snapshot_id", token));
        }
        void Connect()
        {
            if (Environment.OSVersion.Platform != PlatformID.Win32NT) throw new Fault("WINDOWS_REQUIRED", "Live SOLIDWORKS requires Windows x64.");
            if (!Environment.Is64BitProcess) throw new Fault("X64_REQUIRED", "Run the x64 connector.");
            var list = new List<Process>();
            int session = Process.GetCurrentProcess().SessionId;
            foreach (var p in Process.GetProcessesByName("SLDWORKS"))
            {
                if (p.SessionId == session) list.Add(p); else p.Dispose();
            }
            if (list.Count != 1)
            {
                int count = list.Count; foreach (var p in list) p.Dispose();
                throw new Fault(count == 0 ? "SOLIDWORKS_NOT_RUNNING" : "MULTIPLE_SOLIDWORKS",
                    count == 0 ? "Запустите SOLIDWORKS 2026 в той же Windows-сессии, что и Codex." : "Оставьте один экземпляр SOLIDWORKS в этой Windows-сессии. Сохраните работу вручную.");
            }
            string install;
            using (var process = list[0])
            {
                var module = process.MainModule;
                if (module == null || string.IsNullOrEmpty(module.FileName))
                    throw new Fault("SOLIDWORKS_PATH_UNAVAILABLE", "Не удалось прочитать путь работающего SOLIDWORKS. Проверьте одинакового пользователя и уровень прав.");
                install = Path.GetDirectoryName(module.FileName);
                installDir = install;
                SolidWorksProcessId = process.Id;
            }
            // Only the Interop adjacent to the running installation, not an arbitrary caller DLL.
            string[] candidates = {
                Path.Combine(install, "api", "redist", "SolidWorks.Interop.sldworks.dll"),
                Path.Combine(install, "SolidWorks.Interop.sldworks.dll")
            };
            foreach (string candidate in candidates) if (File.Exists(candidate)) { interopPath = candidate; break; }
            if (interopPath == null) throw new Fault("INTEROP_NOT_FOUND", "Не найдена SolidWorks.Interop.sldworks.dll в установленном SOLIDWORKS: " + install + ". Пришлите отчёт CHECK.cmd; не скачивайте случайные DLL.");
            var assemblyName = AssemblyName.GetAssemblyName(interopPath);
            if (assemblyName.Name != "SolidWorks.Interop.sldworks") throw new Fault("INVALID_INTEROP", "Unexpected Interop identity.");
            interop = Assembly.LoadFrom(interopPath);
            string swconstPath = Path.Combine(Path.GetDirectoryName(interopPath), "SolidWorks.Interop.swconst.dll");
            if (File.Exists(swconstPath)) swconst = Assembly.LoadFrom(swconstPath);
            Guid clsid; CLSIDFromProgID("SldWorks.Application", out clsid);
            GetActiveObject(ref clsid, IntPtr.Zero, out app); Track(app);
            revision = Text(Call(app, "ISldWorks", "RevisionNumber"));
            if (revision == null || !revision.StartsWith("34.", StringComparison.Ordinal))
                throw new Fault("UNSUPPORTED_SOLIDWORKS", "Ожидается SOLIDWORKS 2026 (API 34.x), получено: " + revision);
        }
        void Document()
        {
            model = Get(app, "ISldWorks", "IActiveDoc2");
            if (model == null) throw new Fault("NO_ACTIVE_DOCUMENT", "Откройте тестовую деталь, сборку или чертёж в SOLIDWORKS.");
            kind = Convert.ToInt32(Call(model, "IModelDoc2", "GetType"));
            title = Text(Call(model, "IModelDoc2", "GetTitle"));
            path = Text(Call(model, "IModelDoc2", "GetPathName"));
            dirty = Bool(Try("document.has_unsaved_changes", delegate { return Call(model, "IModelDoc2", "GetSaveFlag"); }));
            token = Guid.NewGuid().ToString("N");
            if (kind == 1 || kind == 2)
                config = Text(Try("document.configuration", delegate {
                    var mgr = Get(model, "IModelDoc2", "ConfigurationManager");
                    var cfg = Get(mgr, "IConfigurationManager", "ActiveConfiguration");
                    return Get(cfg, "IConfiguration", "Name");
                }));
        }
        object Context()
        {
            bool localFixed = Program.IsLocalFixedPath(path, true);
            return Json.Obj("title", title, "path", path, "document_type", kind == 1 ? "PART" : kind == 2 ? "ASSEMBLY" : kind == 3 ? "DRAWING" : "UNKNOWN",
                "active_configuration", config, "has_unsaved_changes", dirty, "document_revision", null,
                "storage_scope", Program.IsWorkspacePath(path) ? "WORKSPACE" : localFixed ? "LOCAL_FIXED_DISK" : "NOT_LOCAL_FIXED_DISK",
                "connector_write_allowed", localFixed && (kind == 1 || kind == 3),
                "revision_status", "UNKNOWN", "snapshot_id", token, "captured_at_utc", DateTime.UtcNow.ToString("o"),
                "solidworks_api_revision", revision, "source_state", "IN_MEMORY_ACTIVE_DOCUMENT",
                "note", "API revision is a software version, not the engineering revision. VERIFIED means successfully read, not independently approved. No revision is inferred from filenames or timestamps.");
        }
        object DocumentData()
        {
            if (kind != 3) return Context();
            return Json.Obj("identity", Context(), "sheet_names", Try("drawing.sheet_names", delegate { return Call(model, "IDrawingDoc", "GetSheetNames"); }),
                "scope", "sw_document returns drawing identity and sheet names only. Use sw_drawing for referenced views and displayed-dimension counts; tolerances and notes are not approved.");
        }
        object Properties(string configuration)
        {
            if (configuration == null) return Json.Obj("status", "UNKNOWN", "reason", "Active configuration unavailable", "items", new object[0]);
            var ext = Get(model, "IModelDoc2", "Extension");
            var mgr = Get(ext, "IModelDocExtension", "CustomPropertyManager", configuration);
            var names = Call(mgr, "ICustomPropertyManager", "GetNames") as Array;
            var items = new List<object>();
            int total = names == null ? 0 : names.Length;
            if (names != null)
                foreach (object nameObj in names)
                {
                    if (items.Count >= 200) break;
                    string name = Text(nameObj);
                    object[] args = { name, true, "", "", false, false };
                    object entry = Try("property:" + configuration + ":" + name, delegate {
                        int rc = Convert.ToInt32(Call(mgr, "ICustomPropertyManager", "Get6", args));
                        // swCustomInfoGetResult_e: cached=0, not present=1, resolved=2.
                        string status = rc == 2 && Convert.ToBoolean(args[4]) ? "VERIFIED" : rc == 0 ? "OUTDATED" : "UNKNOWN";
                        return Json.Obj("name", name, "raw", Field(Text(args[2]), "ICustomPropertyManager.Get6", rc == 1 ? "UNKNOWN" : "VERIFIED"),
                            "evaluated", Field(Text(args[3]), "ICustomPropertyManager.Get6", status),
                            "api_return_code", rc, "was_resolved", args[4], "linked", args[5], "scope", configuration == "" ? "DOCUMENT" : configuration);
                    });
                    items.Add(entry ?? Json.Obj("name", name, "status", "UNKNOWN"));
                }
            return Json.Obj("items", items, "total", total, "truncated", total > items.Count,
                "read_mode", "UseCached=true; no configuration switch or forced rebuild");
        }
        object AllProperties()
        {
            return Json.Obj("document", Try("properties.document", delegate { return Properties(""); }),
                "configuration", kind == 3 ? null : Try("properties.configuration", delegate { return Properties(config); }),
                "merge_policy", "Scopes are separate. No automatic material/part-number/revision mapping.");
        }
        object PartData()
        {
            if (kind != 1) throw new Fault("PART_REQUIRED", "sw_part работает с открытой деталью SLDPRT. Для сборки используйте sw_components.");
            var data = Json.Obj();
            object[] args = { config, "" };
            object material = config == null ? null : Try("part.material", delegate { return Call(model, "IPartDoc", "GetMaterialPropertyName2", args); });
            data.Add("material", Field(material, "IPartDoc.GetMaterialPropertyName2"));
            data.Add("material_database", Text(args[1]));
            data.Add("material_scope", "Part active configuration only. Individual body materials may differ.");
            data.Add("bounding_box", Try("part.bounding_box", delegate {
                var a = Call(model, "IPartDoc", "GetPartBox", true) as Array;
                if (a == null || a.Length != 6) throw new Fault("NO_BOUNDING_BOX", "No six-coordinate part box.");
                double[] v = new double[6];
                for (int i = 0; i < 6; i++) v[i] = Convert.ToDouble(a.GetValue(i), CultureInfo.InvariantCulture);
                double[] size = { (v[3] - v[0]) * 1000, (v[4] - v[1]) * 1000, (v[5] - v[2]) * 1000 };
                foreach (double n in size) if (double.IsNaN(n) || double.IsInfinity(n) || n < 0) throw new Fault("INVALID_BOX", "Invalid dimensions.");
                return Json.Obj("size_xyz", Field(size, "IPartDoc.GetPartBox", "CALCULATED", "mm"), "approximate", true,
                    "coordinate_system", "MODEL_AXES", "use", "Approximate envelope only; not drawing dimensions, tolerances or stock size.");
            }));
            data.Add("mass_properties", Try("part.mass_properties", delegate {
                var sel = Get(model, "IModelDoc2", "SelectionManager");
                int selected = Convert.ToInt32(Call(sel, "ISelectionMgr", "GetSelectedObjectCount2", -1));
                if (selected != 0) throw new Fault("SELECTION_PRESENT", "Снимите выделение в SOLIDWORKS вручную, чтобы масса не относилась только к выбранным телам.");
                var ext = Get(model, "IModelDoc2", "Extension");
                var mass = Call(ext, "IModelDocExtension", "CreateMassProperty");
                if (mass == null) throw new Fault("NO_MASS_PROPERTIES", "No mass properties available.");
                // This changes only the temporary calculator's output units, not the model.
                var units = Face("IMassProperty").GetProperty("UseSystemUnits");
                units.SetValue(mass, true, null);
                if (!Convert.ToBoolean(Get(mass, "IMassProperty", "UseSystemUnits"))) throw new Fault("UNITS_UNCONFIRMED", "Cannot confirm SI units.");
                double m = Convert.ToDouble(Get(mass, "IMassProperty", "Mass"));
                double vol = Convert.ToDouble(Get(mass, "IMassProperty", "Volume"));
                double area = Convert.ToDouble(Get(mass, "IMassProperty", "SurfaceArea"));
                foreach (double n in new[] { m, vol, area })
                    if (double.IsNaN(n) || double.IsInfinity(n) || n < 0) throw new Fault("INVALID_MASS_PROPERTIES", "Invalid mass properties.");
                return Json.Obj("mass", Field(m, "IMassProperty.Mass", "CALCULATED", "kg"),
                    "volume", Field(vol, "IMassProperty.Volume", "CALCULATED", "m3"),
                    "surface_area", Field(area, "IMassProperty.SurfaceArea", "CALCULATED", "m2"),
                    "manufacturing_approved", false,
                    "limitations", "CAD-reported values. Density, body materials, overrides, hidden bodies and rebuild freshness are not independently validated. Missing material does not make mass verified.");
            }));
            return data;
        }
        object Components(Dictionary<string, object> args)
        {
            if (kind != 2) throw new Fault("ASSEMBLY_REQUIRED", "Откройте сборку SLDASM.");
            int offset = Catalog.Number(args, "offset", 0, 0, 100000), limit = Catalog.Number(args, "limit", 25, 1, 50);
            var all = Call(model, "IAssemblyDoc", "GetComponents", true) as Array;
            var rows = new List<object>(); int total = all == null ? 0 : all.Length;
            for (int i = offset; i < total && rows.Count < limit; i++)
            {
                var component = Track(all.GetValue(i));
                var row = Json.Obj("index", i);
                row.Add("name", Try("component.name", delegate { return Get(component, "IComponent2", "Name2"); }));
                row.Add("path", Try("component.path", delegate { return Call(component, "IComponent2", "GetPathName"); }));
                row.Add("referenced_configuration", Try("component.configuration", delegate { return Get(component, "IComponent2", "ReferencedConfiguration"); }));
                row.Add("suppression_state_code", Try("component.state", delegate { return Call(component, "IComponent2", "GetSuppression2"); }));
                row.Add("is_suppressed", Try("component.suppressed", delegate { return Call(component, "IComponent2", "IsSuppressed"); }));
                rows.Add(row);
            }
            return Json.Obj("scope", "TOP_LEVEL_INSTANCES", "is_bom", false, "items", rows, "total", total, "offset", offset,
                "next_offset", offset + rows.Count < total ? (object)(offset + rows.Count) : null,
                "truncated", offset > 0 || rows.Count < total,
                "limitations", "Not recursive, not an approved BOM. Suppressed and lightweight components are not resolved. No quantities inferred for manufacturing. Keep assembly unchanged while paging; API order is not guaranteed across calls.");
        }
        static string AssemblySnapshotFingerprint(List<string> sortedInstanceIds)
        {
            string joined = string.Join("\n", sortedInstanceIds.ConvertAll(delegate(string id) { return id == null ? "::NULL::" : id; }));
            using (var sha = SHA256.Create())
            {
                byte[] hash = sha.ComputeHash(Encoding.UTF8.GetBytes(joined));
                return BitConverter.ToString(hash).Replace("-", "").ToLowerInvariant().Substring(0, 32);
            }
        }
        object AssemblyTree(Dictionary<string, object> args)
        {
            if (kind != 2) throw new Fault("ASSEMBLY_REQUIRED", "Откройте сборку SLDASM.");
            int offset = Catalog.Number(args, "offset", 0, 0, 100000), limit = Catalog.Number(args, "limit", 25, 1, 50);
            // One single API call forms the entire snapshot for this invocation; every instance is
            // read from this one array only, never re-fetched, so a page can never straddle two
            // different live reads of the assembly.
            var all = Call(model, "IAssemblyDoc", "GetComponents", false) as Array;
            int rawTotal = all == null ? 0 : all.Length;
            var entries = new List<object[]>(rawTotal); // [0]=instanceId (string, may be null), [1]=component (COM object)
            for (int i = 0; i < rawTotal; i++)
            {
                var component = Track(all.GetValue(i));
                string instanceId = Try("component.instance_id:" + i, delegate { return Get(component, "IComponent2", "Name2"); }) as string;
                entries.Add(new object[] { instanceId, component });
            }
            // IAssemblyDoc.GetComponents does not guarantee the same order across separate calls
            // (separate connector invocations included). Name2 is SOLIDWORKS's own unique, stable
            // hierarchical instance identifier, so sorting by it makes offset-based paging
            // deterministic and repeatable across calls as long as the assembly itself is unchanged.
            entries.Sort(delegate(object[] a, object[] b) {
                string ka = (string)a[0], kb = (string)b[0];
                if (ka == null && kb == null) return 0;
                if (ka == null) return 1;
                if (kb == null) return -1;
                return string.CompareOrdinal(ka, kb);
            });
            int total = entries.Count;
            var sortedIds = new List<string>(total);
            foreach (var entry in entries) sortedIds.Add((string)entry[0]);
            string snapshotId = AssemblySnapshotFingerprint(sortedIds);
            int lightweightCode = -1;
            bool lightweightCodeKnown = false;
            var rows = new List<object>();
            for (int i = offset; i < total && rows.Count < limit; i++)
            {
                string instanceId = (string)entries[i][0];
                var component = entries[i][1];
                var row = Json.Obj("index", i, "instance_id", instanceId);
                row.Add("name", Try("component.name:" + i, delegate { return Get(component, "IComponent2", "Name2"); }));
                row.Add("path", Try("component.path:" + i, delegate { return Call(component, "IComponent2", "GetPathName"); }));
                row.Add("referenced_configuration", Try("component.configuration:" + i, delegate { return Get(component, "IComponent2", "ReferencedConfiguration"); }));
                object suppressionCode = Try("component.state:" + i, delegate { return Call(component, "IComponent2", "GetSuppression2"); });
                row.Add("suppression_state_code", suppressionCode);
                row.Add("is_suppressed", Try("component.suppressed:" + i, delegate { return Call(component, "IComponent2", "IsSuppressed"); }));
                row.Add("is_virtual", Try("component.is_virtual:" + i, delegate { return Get(component, "IComponent2", "IsVirtual"); }));
                object isLightweight = null;
                if (suppressionCode != null)
                {
                    isLightweight = Try("component.is_lightweight:" + i, delegate {
                        if (!lightweightCodeKnown) { lightweightCode = EnumValue("swComponentSuppressionState_e", "swComponentLightweight"); lightweightCodeKnown = true; }
                        return Convert.ToInt32(suppressionCode, CultureInfo.InvariantCulture) == lightweightCode;
                    });
                }
                row.Add("is_lightweight", isLightweight);
                object parentInstanceId = Try("component.parent:" + i, delegate {
                    var parent = Call(component, "IComponent2", "GetParent");
                    return parent == null ? null : Get(parent, "IComponent2", "Name2");
                });
                row.Add("parent_instance_id", parentInstanceId);
                row.Add("is_top_level", parentInstanceId == null);
                rows.Add(row);
            }
            return Json.Obj("scope", "FULL_RECURSIVE_INSTANCES", "is_bom", false, "snapshot_id", snapshotId, "items", rows, "total", total, "offset", offset,
                "next_offset", offset + rows.Count < total ? (object)(offset + rows.Count) : null,
                "truncated", offset > 0 || rows.Count < total,
                "limitations", "Every component instance at every level, flattened by one call to IAssemblyDoc.GetComponents(bTopOnly=false); not grouped or deduplicated by path+configuration and not an approved BOM. Rows are sorted by instance_id (IComponent2.Name2, SOLIDWORKS's own unique hierarchical instance name) before paging, so snapshot_id and offsets are repeatable across separate calls as long as the assembly is unchanged; a different snapshot_id on a later call means the component set changed between reads and pages should not be combined. parent_instance_id is the parent's own instance_id (null meaning it sits directly under the root). Suppressed, lightweight and virtual components are listed with their state flags but not resolved further.");
        }
        // Standalone property reader for ComponentDetails: deliberately does not reuse
        // Properties()/PropertiesFor() or Field(), which are tied to the class-level active
        // document (model/path/config/token). Reading an assembly component's OWN document
        // must never be able to mislabel its data as coming from the active assembly, so this
        // duplicates the same ICustomPropertyManager.Get6 logic against an explicit targetModel
        // and tags every item with the explicit sourceDocumentPath supplied by the caller.
        object ComponentPropertiesFor(object targetModel, string configuration, string sourceDocumentPath)
        {
            if (configuration == null) return Json.Obj("status", "UNKNOWN", "reason", "Configuration unavailable", "items", new object[0]);
            var ext = Get(targetModel, "IModelDoc2", "Extension");
            var mgr = Get(ext, "IModelDocExtension", "CustomPropertyManager", configuration);
            var names = Call(mgr, "ICustomPropertyManager", "GetNames") as Array;
            var items = new List<object>();
            int total = names == null ? 0 : names.Length;
            if (names != null)
                foreach (object nameObj in names)
                {
                    if (items.Count >= 200) break;
                    string name = Text(nameObj);
                    object[] args = { name, true, "", "", false, false };
                    object entry = Try("component_property:" + sourceDocumentPath + ":" + configuration + ":" + name, delegate {
                        int rc = Convert.ToInt32(Call(mgr, "ICustomPropertyManager", "Get6", args));
                        // swCustomInfoGetResult_e: cached=0, not present=1, resolved=2.
                        string status = rc == 2 && Convert.ToBoolean(args[4]) ? "VERIFIED" : rc == 0 ? "OUTDATED" : "UNKNOWN";
                        return Json.Obj("name", name, "raw", Text(args[2]), "evaluated", Text(args[3]), "value_status", status,
                            "api_return_code", rc, "was_resolved", args[4], "linked", args[5], "scope", configuration == "" ? "DOCUMENT" : configuration);
                    });
                    items.Add(entry ?? Json.Obj("name", name, "status", "UNKNOWN"));
                }
            return Json.Obj("items", items, "total", total, "truncated", total > items.Count,
                "read_mode", "UseCached=true; no configuration switch or forced rebuild", "source_document", sourceDocumentPath);
        }
        object ComponentDetails(Dictionary<string, object> args)
        {
            if (kind != 2) throw new Fault("ASSEMBLY_REQUIRED", "Откройте сборку SLDASM.");
            string instanceId = Catalog.TextValue(args, "instance_id", true, 2048);
            var all = Call(model, "IAssemblyDoc", "GetComponents", false) as Array;
            int total = all == null ? 0 : all.Length;
            object matchComponent = null;
            for (int i = 0; i < total; i++)
            {
                var component = Track(all.GetValue(i));
                string id = Try("component.instance_id:" + i, delegate { return Get(component, "IComponent2", "Name2"); }) as string;
                if (matchComponent == null && string.Equals(id, instanceId, StringComparison.Ordinal)) matchComponent = component;
            }
            if (matchComponent == null)
                throw new Fault("COMPONENT_NOT_FOUND", "No component instance of the active assembly currently has this instance_id. Re-read sw_assembly_tree or sw_components; instance_id values are only valid while the assembly's component set is unchanged.");
            var row = Json.Obj("instance_id", instanceId);
            string componentPath = Try("component.path", delegate { return Call(matchComponent, "IComponent2", "GetPathName"); }) as string;
            row.Add("path", componentPath);
            string referencedConfig = Try("component.configuration", delegate { return Get(matchComponent, "IComponent2", "ReferencedConfiguration"); }) as string;
            row.Add("referenced_configuration", referencedConfig);
            object suppressionCode = Try("component.state", delegate { return Call(matchComponent, "IComponent2", "GetSuppression2"); });
            row.Add("suppression_state_code", suppressionCode);
            bool? isSuppressed = Bool(Try("component.suppressed", delegate { return Call(matchComponent, "IComponent2", "IsSuppressed"); }));
            row.Add("is_suppressed", isSuppressed);
            row.Add("is_virtual", Try("component.is_virtual", delegate { return Get(matchComponent, "IComponent2", "IsVirtual"); }));
            object componentModel = null;
            string resolveReason = null;
            if (isSuppressed == true)
                resolveReason = "Component is suppressed; SOLIDWORKS does not keep a loaded model document for a suppressed component.";
            else
            {
                componentModel = Try("component.model_doc", delegate { return Call(matchComponent, "IComponent2", "GetModelDoc2"); });
                if (componentModel == null)
                    resolveReason = "IComponent2.GetModelDoc2() returned null: the component's own document is not currently loaded in memory (for example an unresolved/missing reference, or a lightweight state not backed by a loaded document). Nothing was opened to force a load.";
            }
            row.Add("resolved", componentModel != null);
            row.Add("resolve_reason", resolveReason);
            string componentDocPath = null, componentDocType = null, propertiesConfigUsed = null;
            object properties = null, material = null, massProperties = null;
            if (componentModel != null)
            {
                componentDocPath = Try("component.model_doc.path", delegate { return Call(componentModel, "IModelDoc2", "GetPathName"); }) as string;
                object componentKindObj = Try("component.model_doc.type", delegate { return Call(componentModel, "IModelDoc2", "GetType"); });
                int componentKind = componentKindObj == null ? -1 : Convert.ToInt32(componentKindObj, CultureInfo.InvariantCulture);
                componentDocType = componentKind == 1 ? "PART" : componentKind == 2 ? "ASSEMBLY" : "UNKNOWN";
                propertiesConfigUsed = referencedConfig;
                if (string.IsNullOrEmpty(propertiesConfigUsed))
                    propertiesConfigUsed = Try("component.model_doc.active_configuration", delegate {
                        var mgr = Get(componentModel, "IModelDoc2", "ConfigurationManager");
                        var cfg = Get(mgr, "IConfigurationManager", "ActiveConfiguration");
                        return Get(cfg, "IConfiguration", "Name");
                    }) as string;
                string docPathForSource = componentDocPath ?? componentPath;
                properties = Try("component.properties", delegate {
                    return Json.Obj("document", ComponentPropertiesFor(componentModel, "", docPathForSource),
                        "configuration", string.IsNullOrEmpty(propertiesConfigUsed) ? null : ComponentPropertiesFor(componentModel, propertiesConfigUsed, docPathForSource));
                });
                if (componentKind == 1)
                    material = Try("component.material", delegate {
                        object[] matArgs = { propertiesConfigUsed, "" };
                        object mat = Call(componentModel, "IPartDoc", "GetMaterialPropertyName2", matArgs);
                        return Json.Obj("name", Text(mat), "database", Text(matArgs[1]));
                    });
                massProperties = Try("component.mass_properties", delegate {
                    // GetModelDoc2 may represent a different configuration from this instance.
                    string activeConfiguration = ActiveConfigurationOf(componentModel);
                    if (string.IsNullOrWhiteSpace(referencedConfig) || string.IsNullOrWhiteSpace(activeConfiguration))
                        throw new Fault("COMPONENT_MASS_CONFIGURATION_UNKNOWN", "Cannot confirm the referenced and loaded configurations; mass properties were not read.");
                    if (!string.Equals(referencedConfig, activeConfiguration, StringComparison.Ordinal))
                        throw new Fault("COMPONENT_MASS_CONFIGURATION_MISMATCH", "Referenced configuration '" + referencedConfig +
                            "' differs from loaded configuration '" + activeConfiguration + "'; mass properties were not read. No configuration was switched.");
                    var ext = Get(componentModel, "IModelDoc2", "Extension");
                    var mass = Call(ext, "IModelDocExtension", "CreateMassProperty");
                    if (mass == null) throw new Fault("NO_MASS_PROPERTIES", "No mass properties available.");
                    var units = Face("IMassProperty").GetProperty("UseSystemUnits");
                    units.SetValue(mass, true, null);
                    if (!Convert.ToBoolean(Get(mass, "IMassProperty", "UseSystemUnits"))) throw new Fault("UNITS_UNCONFIRMED", "Cannot confirm SI units.");
                    double m = Convert.ToDouble(Get(mass, "IMassProperty", "Mass"));
                    double vol = Convert.ToDouble(Get(mass, "IMassProperty", "Volume"));
                    double area = Convert.ToDouble(Get(mass, "IMassProperty", "SurfaceArea"));
                    foreach (double n in new[] { m, vol, area })
                        if (double.IsNaN(n) || double.IsInfinity(n) || n < 0) throw new Fault("INVALID_MASS_PROPERTIES", "Invalid mass properties.");
                    if (!string.Equals(activeConfiguration, ActiveConfigurationOf(componentModel), StringComparison.Ordinal))
                        throw new Fault("COMPONENT_MASS_CONFIGURATION_CHANGED", "The loaded configuration changed while reading mass properties; discard the result.");
                    return Json.Obj("mass_kg", m, "volume_m3", vol, "surface_area_m2", area,
                        "configuration", activeConfiguration);
                });
            }
            row.Add("component_document_type", componentDocType);
            row.Add("component_document_path", componentDocPath);
            row.Add("properties_configuration_used", propertiesConfigUsed);
            row.Add("properties", properties);
            row.Add("material", material);
            row.Add("mass_properties", massProperties);
            row.Add("mass_properties_status", massProperties == null ? "UNKNOWN" : "VERIFIED");
            return Json.Obj("operation", "COMPONENT_DETAILS", "component", row,
                "api", "IComponent2 fields from the active assembly's own IAssemblyDoc.GetComponents(bTopOnly=false); properties/material/mass_properties come from the component's OWN already-loaded IModelDoc2 (IComponent2.GetModelDoc2()) and never open, activate or switch any document.",
                "opens_document", false,
                "scope_note", "material and mass_properties describe the unique file+configuration this instance references (its own document), not this instance's position, orientation, transform or quantity within the assembly. Mass properties are returned only when the loaded document's active configuration matches the referenced configuration before and after the read; otherwise they remain null with status UNKNOWN (see issues or resolve_reason). No configuration is switched. Classifying purchased/manufactured, missing-path or suppressed STATUS from these raw fields (for a BOM/inventory report) is left to the caller; this tool reports facts only.",
                "manufacturing_approved", false);
        }
        string ActiveConfigurationOf(object target)
        {
            var manager = Get(target, "IModelDoc2", "ConfigurationManager");
            var configuration = Get(manager, "IConfigurationManager", "ActiveConfiguration");
            return Text(Get(configuration, "IConfiguration", "Name"));
        }
        object EquationsData()
        {
            if (kind != 1 && kind != 2) throw new Fault("PART_OR_ASSEMBLY_REQUIRED", "sw_equations работает с открытой деталью SLDPRT или сборкой SLDASM.");
            var mgr = Try("equations.manager", delegate { return Call(model, "IModelDoc2", "GetEquationMgr"); });
            if (mgr == null)
                return Json.Obj("scope", "DOCUMENT_EQUATIONS_AND_GLOBAL_VARIABLES", "items", new object[0], "total", 0,
                    "status", "UNKNOWN", "reason", "IModelDoc2.GetEquationMgr() unavailable or failed on this document.");
            int total = 0;
            object countResult = Try("equations.count", delegate { return Call(mgr, "IEquationMgr", "GetCount"); });
            if (countResult != null) total = Convert.ToInt32(countResult, CultureInfo.InvariantCulture);
            var rows = new List<object>();
            for (int i = 0; i < total; i++)
            {
                int index = i;
                var row = Json.Obj("index", index);
                row.Add("text", Try("equation.text:" + index, delegate { return Get(mgr, "IEquationMgr", "Equation", index); }));
                row.Add("is_global_variable", Try("equation.is_global_variable:" + index, delegate { return Get(mgr, "IEquationMgr", "GlobalVariable", index); }));
                row.Add("is_suppressed", Try("equation.is_suppressed:" + index, delegate { return Get(mgr, "IEquationMgr", "Suppression", index); }));
                row.Add("configuration_option", Try("equation.configuration_option:" + index, delegate { return Call(mgr, "IEquationMgr", "GetConfigurationOption", index); }));
                row.Add("configuration_name", null);
                row.Add("configuration_name_status", "UNKNOWN");
                row.Add("configuration_name_reason", "IEquationMgr does not expose a getter for the equation's configuration-name list. No scope names are inferred from the active configuration.");
                rows.Add(row);
            }
            return Json.Obj("scope", "DOCUMENT_EQUATIONS_AND_GLOBAL_VARIABLES", "items", rows, "total", total,
                "limitations", "Raw IEquationMgr contents only: exact equation text (\"LHS\" = RHS) and whatever global-variable/suppression/configuration-scope flags the installed API revision exposes; a flag that is unavailable is reported as an UNKNOWN issue, never guessed. No formula is evaluated, renamed or classified by the connector; sorting equations into input/derived/fixed is a downstream analysis step.");
        }
        object ConfigurationsData()
        {
            if (kind != 1 && kind != 2) throw new Fault("PART_OR_ASSEMBLY_REQUIRED", "sw_configurations работает с открытой деталью SLDPRT или сборкой SLDASM.");
            var namesResult = Try("configurations.names", delegate { return Call(model, "IModelDoc2", "GetConfigurationNames"); });
            var names = namesResult as Array;
            var list = new List<object>();
            if (names != null) foreach (object n in names) list.Add(Text(n));
            return Json.Obj("scope", "DOCUMENT_CONFIGURATIONS", "items", list, "total", list.Count,
                "active_configuration", config,
                "limitations", "Configuration names only, from IModelDoc2.GetConfigurationNames(). Per-configuration suppression state and Design Table linkage are not read here.");
        }
        static string FileNumber(double value)
        {
            return value.ToString("0.###", CultureInfo.InvariantCulture).Replace('.', 'p');
        }
        static void FindTemplatesUnder(string root, string pattern, List<string> found)
        {
            if (string.IsNullOrWhiteSpace(root) || !Directory.Exists(root)) return;
            var pending = new Queue<string>();
            var seen = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
            pending.Enqueue(root); int visited = 0;
            while (pending.Count > 0 && visited++ < 2500 && found.Count < 100)
            {
                string current = pending.Dequeue();
                if (!seen.Add(current)) continue;
                try
                {
                    var info = new DirectoryInfo(current);
                    if ((info.Attributes & FileAttributes.ReparsePoint) != 0) continue;
                    foreach (string file in Directory.GetFiles(current, pattern, SearchOption.TopDirectoryOnly))
                        if (found.Count < 100) found.Add(file);
                    foreach (string directory in Directory.GetDirectories(current)) pending.Enqueue(directory);
                }
                catch { }
            }
        }
        string FindPartTemplate(out string source)
        {
            source = "configured_default";
            int pref = EnumValue("swUserPreferenceStringValue_e", "swDefaultTemplatePart");
            string configured = Text(Call(app, "ISldWorks", "GetUserPreferenceStringValue", pref));
            if (!string.IsNullOrWhiteSpace(configured) && File.Exists(configured)) return configured;

            var candidates = new List<string>();
            FindTemplatesUnder(Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.CommonApplicationData), "SOLIDWORKS"), "*.prtdot", candidates);
            FindTemplatesUnder(installDir, "*.prtdot", candidates);
            FindTemplatesUnder(Environment.GetFolderPath(Environment.SpecialFolder.MyDocuments), "*.prtdot", candidates);
            if (candidates.Count == 0)
                throw new Fault("PART_TEMPLATE_NOT_FOUND", "No .prtdot template was found in the configured default path, ProgramData\\SOLIDWORKS, the running SOLIDWORKS installation, or Documents.");
            candidates.Sort(delegate(string a, string b) {
                Func<string, int> score = delegate(string p) {
                    string lower = p.ToLowerInvariant(); int n = 0;
                    if (lower.Contains("template") || lower.Contains("шаблон")) n += 20;
                    string name = Path.GetFileNameWithoutExtension(lower);
                    if (name == "part" || name == "деталь") n += 100;
                    if (lower.Contains("tutorial")) n -= 20;
                    return n;
                };
                int byScore = score(b).CompareTo(score(a));
                return byScore != 0 ? byScore : StringComparer.OrdinalIgnoreCase.Compare(a, b);
            });
            source = "discovered_prtdot";
            return candidates[0];
        }
        string FindDrawingTemplate(out string source)
        {
            source = "configured_default";
            int pref = EnumValue("swUserPreferenceStringValue_e", "swDefaultTemplateDrawing");
            string configured = Text(Call(app, "ISldWorks", "GetUserPreferenceStringValue", pref));
            if (!string.IsNullOrWhiteSpace(configured) && File.Exists(configured)) return configured;

            var candidates = new List<string>();
            FindTemplatesUnder(Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.CommonApplicationData), "SOLIDWORKS"), "*.drwdot", candidates);
            FindTemplatesUnder(installDir, "*.drwdot", candidates);
            FindTemplatesUnder(Environment.GetFolderPath(Environment.SpecialFolder.MyDocuments), "*.drwdot", candidates);
            if (candidates.Count == 0)
                throw new Fault("DRAWING_TEMPLATE_NOT_FOUND", "No .drwdot template was found. Configure a default drawing template in SOLIDWORKS System Options or place a drawing template in the standard templates folder.");
            candidates.Sort(delegate(string a, string b) {
                Func<string, int> score = delegate(string p) {
                    string lower = p.ToLowerInvariant(); int n = 0;
                    if (lower.Contains("template") || lower.Contains("шаблон")) n += 20;
                    string name = Path.GetFileNameWithoutExtension(lower);
                    if (name == "drawing" || name == "чертеж" || name == "чертёж") n += 100;
                    if (lower.Contains("gost") || lower.Contains("гост")) n += 30;
                    if (lower.Contains("tutorial")) n -= 20;
                    return n;
                };
                int byScore = score(b).CompareTo(score(a));
                return byScore != 0 ? byScore : StringComparer.OrdinalIgnoreCase.Compare(a, b);
            });
            source = "discovered_drwdot";
            return candidates[0];
        }
        static string UniqueWorkspacePath(string stem, string extension)
        {
            string root = Program.EnsureWorkspace();
            string clean = stem;
            foreach (char c in Path.GetInvalidFileNameChars()) clean = clean.Replace(c, '_');
            if (clean.Length > 80) clean = clean.Substring(0, 80);
            string name = clean + "_" + DateTime.UtcNow.ToString("yyyyMMdd_HHmmss") + "_" +
                Guid.NewGuid().ToString("N").Substring(0, 8) + extension;
            string result = Path.Combine(root, name);
            if (!Program.IsWorkspacePath(result) || File.Exists(result))
                throw new Fault("WORKSPACE_PATH_FAILED", "Cannot allocate a unique file in the local workspace.");
            return result;
        }
        static string UniqueSiblingPath(string sourcePath, string suffix, string extension)
        {
            string source = Program.RequireLocalFixedPath(sourcePath, true);
            string directory = Path.GetDirectoryName(source);
            string stem = Path.GetFileNameWithoutExtension(source) + suffix;
            foreach (char c in Path.GetInvalidFileNameChars()) stem = stem.Replace(c, '_');
            if (stem.Length > 120) stem = stem.Substring(0, 120);
            string name = stem + "_" + DateTime.UtcNow.ToString("yyyyMMdd_HHmmss") + "_" +
                Guid.NewGuid().ToString("N").Substring(0, 8) + extension;
            string result = Path.Combine(directory, name);
            Program.RequireLocalFixedPath(result, false);
            if (File.Exists(result))
                throw new Fault("LOCAL_OUTPUT_PATH_FAILED", "Cannot allocate a unique file beside the local source document.");
            return result;
        }
        static string UniqueLocalOutputPath(string sourcePath, string suffix, string extension)
        {
            return Program.IsWorkspacePath(sourcePath)
                ? UniqueWorkspacePath(Path.GetFileNameWithoutExtension(sourcePath) + suffix, extension)
                : UniqueSiblingPath(sourcePath, suffix, extension);
        }
        static string FileSha256(string filePath)
        {
            using (var sha = SHA256.Create())
            using (var stream = new FileStream(filePath, FileMode.Open, FileAccess.Read,
                FileShare.ReadWrite | FileShare.Delete))
                return BitConverter.ToString(sha.ComputeHash(stream)).Replace("-", "").ToLowerInvariant();
        }
        static string CreateLocalBackup(string sourcePath, string suffix)
        {
            string source = Program.RequireLocalFixedPath(sourcePath, true);
            string backup = UniqueLocalOutputPath(source, suffix, Path.GetExtension(source));
            string expectedHash = FileSha256(source);
            File.Copy(source, backup, false);
            if (!File.Exists(backup) || !string.Equals(FileSha256(backup), expectedHash, StringComparison.Ordinal))
                throw new Fault("BACKUP_FAILED", "Cannot verify the automatic local pre-change backup.");
            return backup;
        }
        static void RequireWorkspacePath(string filePath)
        {
            if (!Program.IsWorkspacePath(filePath))
                throw new Fault("WORKSPACE_REQUIRED", "This operation is allowed only for a file inside the local SolidWorksCodex Workspace folder. Copy the active part with sw_copy_active_to_workspace first.");
        }
        object WorkspaceStatus(Dictionary<string, object> args)
        {
            string root = Program.EnsureWorkspace();
            int limit = Catalog.Number(args, "limit", 50, 1, 100);
            var files = new List<FileInfo>();
            foreach (string item in Directory.GetFiles(root, "*", SearchOption.TopDirectoryOnly))
            {
                string extension = Path.GetExtension(item);
                if (!string.Equals(extension, ".SLDPRT", StringComparison.OrdinalIgnoreCase) &&
                    !string.Equals(extension, ".SLDDRW", StringComparison.OrdinalIgnoreCase) &&
                    !string.Equals(extension, ".PDF", StringComparison.OrdinalIgnoreCase)) continue;
                if (!Program.IsWorkspacePath(item)) continue;
                files.Add(new FileInfo(item));
            }
            files.Sort(delegate(FileInfo a, FileInfo b) { return b.LastWriteTimeUtc.CompareTo(a.LastWriteTimeUtc); });
            var rows = new List<object>();
            for (int i = 0; i < files.Count && i < limit; i++)
                rows.Add(Json.Obj("file_name", files[i].Name, "type",
                    string.Equals(files[i].Extension, ".SLDPRT", StringComparison.OrdinalIgnoreCase) ? "PART" :
                    string.Equals(files[i].Extension, ".SLDDRW", StringComparison.OrdinalIgnoreCase) ? "DRAWING" : "PDF",
                    "size_bytes", files[i].Length, "modified_at_utc", files[i].LastWriteTimeUtc.ToString("o")));
            return Json.Obj("workspace_path", root, "local_only", true, "pdm_operations", false,
                "files", rows.ToArray(), "total", files.Count, "truncated", files.Count > rows.Count,
                "policy", "New model creation uses Workspace. Existing active SLDPRT and SLDDRW files may be changed only on a verified local fixed disk. UNC, mapped network, removable and reparse paths are blocked. Assemblies, macros and arbitrary COM calls are not accepted.");
        }
        object OpenLocalPath(string filePath, bool allowAssembly = false, bool requestReadOnly = false,
            bool requireCleanLoad = false)
        {
            filePath = Program.RequireLocalFixedPath(filePath, true);
            string extension = Path.GetExtension(filePath);
            int documentType = string.Equals(extension, ".SLDPRT", StringComparison.OrdinalIgnoreCase) ? 1 :
                string.Equals(extension, ".SLDDRW", StringComparison.OrdinalIgnoreCase) ? 3 :
                (allowAssembly && string.Equals(extension, ".SLDASM", StringComparison.OrdinalIgnoreCase)) ? 2 : 0;
            if (documentType == 0) throw new Fault("LOCAL_FILE_TYPE", allowAssembly
                ? "Only local SLDPRT, SLDASM and SLDDRW files can be opened."
                : "Only local SLDPRT and SLDDRW files can be opened.");
            // OpenDoc6 does not change the access mode of a document that is already open in this
            // SOLIDWORKS session: it just activates the existing in-memory document as-is, so a
            // requested read-only option is silently ignored for a document left open read-write by
            // an earlier call. Detect that case via the real API. This connector never closes or
            // reopens a document it did not itself open: if the already-open document is confirmed
            // read-only (IModelDoc2.IsOpenedReadOnly), it is reused as-is; otherwise the caller is
            // told to close it manually in SOLIDWORKS. Closing another session's document, even one
            // with no unsaved changes, is out of scope for this connector.
            object activated = null;
            int errors = 0;
            int warnings = 0;
            bool reusedAlreadyOpenReadOnly = false;
            string openStatus = null;
            if (requestReadOnly)
            {
                object alreadyOpen = Try("document.already_open_check", delegate {
                    return Call(app, "ISldWorks", "GetOpenDocumentByName", filePath);
                });
                if (alreadyOpen != null)
                {
                    object state = Try("document.already_open_read_only_state", delegate {
                        return Call(alreadyOpen, "IModelDoc2", "IsOpenedReadOnly");
                    });
                    bool confirmedReadOnlyAlready = state != null && Convert.ToBoolean(state, CultureInfo.InvariantCulture);
                    if (!confirmedReadOnlyAlready)
                        throw new Fault("ASSEMBLY_ALREADY_OPEN_NOT_READONLY",
                            "The document is already open in this SOLIDWORKS session and is not confirmed read-only (IModelDoc2.IsOpenedReadOnly() returned false, or the state could not be confirmed). This connector will not close or reopen a document it did not open itself. Close it manually in SOLIDWORKS and try again.");
                    string alreadyOpenTitle = Text(Try("document.already_open_title", delegate {
                        return Call(alreadyOpen, "IModelDoc2", "GetTitle");
                    }));
                    if (string.IsNullOrEmpty(alreadyOpenTitle))
                        throw new Fault("ASSEMBLY_ALREADY_OPEN_NOT_READONLY",
                            "The document is already open read-only in this SOLIDWORKS session but its title could not be confirmed, so it cannot be safely reused.");
                    activated = ActivateDocumentByTitle(alreadyOpenTitle);
                    reusedAlreadyOpenReadOnly = true;
                    openStatus = "REUSED_ALREADY_OPEN";
                }
            }
            if (activated == null)
            {
                int options = EnumValue("swOpenDocOptions_e", "swOpenDocOptions_Silent");
                if (requestReadOnly) options |= EnumValue("swOpenDocOptions_e", "swOpenDocOptions_ReadOnly");
                object[] openArgs = { filePath, documentType, options, "", 0, 0 };
                object opened = Call(app, "ISldWorks", "OpenDoc6", openArgs);
                errors = Convert.ToInt32(openArgs[4], CultureInfo.InvariantCulture);
                warnings = Convert.ToInt32(openArgs[5], CultureInfo.InvariantCulture);
                // A partial load is usable for confirmed read-only inspection, not for editing.
                // Variant creation additionally rejects warnings, which may indicate missing data.
                if (opened == null)
                    throw new Fault("OPEN_FAILED", "SOLIDWORKS did not open the local file (OpenDoc6 returned no document). errors=" + errors + ", warnings=" + warnings);
                if (errors != 0 && (!requestReadOnly || requireCleanLoad))
                    throw new Fault("OPEN_LOAD_ERRORS", "SOLIDWORKS returned a document with load errors; further operations are blocked. errors=" + errors + ", warnings=" + warnings);
                if (requireCleanLoad && warnings != 0)
                    throw new Fault("OPEN_LOAD_WARNINGS", "A clean load is required before modifying a variant. errors=" + errors + ", warnings=" + warnings);
                string openedTitle = Text(Call(opened, "IModelDoc2", "GetTitle"));
                if (string.IsNullOrEmpty(openedTitle))
                    throw new Fault("OPEN_FAILED", "OpenDoc6 returned a document but its title could not be read, so it cannot be safely activated. errors=" + errors + ", warnings=" + warnings);
                activated = ActivateDocumentByTitle(openedTitle);
                openStatus = errors != 0 ? "OPENED_WITH_LOAD_ERRORS" :
                    warnings != 0 ? "OPENED_WITH_WARNINGS" : "OPENED_CLEAN";
            }
            string confirmed = Text(Call(activated, "IModelDoc2", "GetPathName"));
            if (!string.Equals(Path.GetFullPath(confirmed), Path.GetFullPath(filePath), StringComparison.OrdinalIgnoreCase) ||
                !Program.IsLocalFixedPath(confirmed, true))
                throw new Fault("LOCAL_FILE_VERIFICATION_FAILED", "The active SOLIDWORKS document is not the requested local fixed-disk file.");
            if (Convert.ToInt32(Call(activated, "IModelDoc2", "GetType"), CultureInfo.InvariantCulture) != documentType)
                throw new Fault("LOCAL_FILE_TYPE_MISMATCH", "The opened document type does not match the requested file extension.");
            // Do not trust the requested open option: ask the document itself whether it is actually
            // read-only. Only a confirmed answer from the API may become a boolean; anything else is UNKNOWN.
            object confirmedReadOnly = null;
            if (requestReadOnly)
            {
                confirmedReadOnly = "UNKNOWN";
                object state = Try("document.read_only_state", delegate {
                    return Call(activated, "IModelDoc2", "IsOpenedReadOnly");
                });
                if (state != null) confirmedReadOnly = Convert.ToBoolean(state, CultureInfo.InvariantCulture);
                if (!object.Equals(confirmedReadOnly, true))
                    throw new Fault("READ_ONLY_NOT_CONFIRMED", "SOLIDWORKS did not confirm read-only access. The document was left open without saving or closing it. errors=" + errors + ", warnings=" + warnings);
            }
            return Json.Obj("model", activated, "errors", errors, "warnings", warnings, "path", confirmed,
                "document_type", documentType == 1 ? "PART" : documentType == 2 ? "ASSEMBLY" : "DRAWING",
                "confirmed_read_only", confirmedReadOnly,
                "reused_already_open_read_only", reusedAlreadyOpenReadOnly,
                "open_status", openStatus,
                "open_status_note", "OPENED_CLEAN: OpenDoc6 reported errors=0 and warnings=0. OPENED_WITH_WARNINGS: a document was opened with warnings (see warnings); this is not an unqualified PASS. OPENED_WITH_LOAD_ERRORS: a document was opened with errors for confirmed read-only inspection only (see errors/warnings). Variant creation requires both codes to be zero for the source and the copy. REUSED_ALREADY_OPEN: an already-open document confirmed read-only was reused without calling OpenDoc6 again; errors=0/warnings=0 here reflect that no new open call was made, not a report about the original load.");
        }
        object ActivateDocumentByTitle(string titleToActivate)
        {
            object[] activateArgs = { titleToActivate, true, 0 };
            object activated = Call(app, "ISldWorks", "ActivateDoc2", activateArgs);
            int activateErrors = Convert.ToInt32(activateArgs[2], CultureInfo.InvariantCulture);
            if (activated == null || activateErrors != 0)
                throw new Fault("ACTIVATE_FAILED", "SOLIDWORKS did not activate the local file. errors=" + activateErrors);
            return activated;
        }
        object OpenAssemblyReadOnly(Dictionary<string, object> args)
        {
            string requestedPath = Catalog.LocalAssemblyPathText(args, "file_path");
            string verifiedPath = Program.RequireLocalFixedPath(requestedPath, true);
            object result = OpenLocalPath(verifiedPath, true, true);
            var resultMap = Json.Map(result);
            string documentType = Text(Json.At(resultMap, "document_type"));
            if (documentType != "ASSEMBLY")
                throw new Fault("ASSEMBLY_REQUIRED", "file_path must be an .SLDASM assembly. Use sw_open_local_file for parts or drawings.");
            return Json.Obj("operation", "OPENED_ASSEMBLY_READ_ONLY", "connector_version", Program.Version,
                "file_path", Json.At(resultMap, "path"),
                "document_type", documentType,
                "open_errors", Json.At(resultMap, "errors"),
                "open_warnings", Json.At(resultMap, "warnings"),
                "open_status", Json.At(resultMap, "open_status"),
                "open_status_note", Json.At(resultMap, "open_status_note"),
                "inside_workspace", Program.IsWorkspacePath(verifiedPath),
                "local_fixed_disk_only", true, "network_paths_allowed", false,
                "open_options", "swOpenDocOptions_Silent | swOpenDocOptions_ReadOnly",
                "read_only", Json.At(resultMap, "confirmed_read_only"),
                "read_only_source", "IModelDoc2.IsOpenedReadOnly() confirmed after activation; false or unavailable state fails the operation. Never assumed true from the requested open option.",
                "reused_already_open_read_only", Json.At(resultMap, "reused_already_open_read_only"),
                "reused_already_open_read_only_note", "true only when the document was already open in this SOLIDWORKS session and IModelDoc2.IsOpenedReadOnly() confirmed it was already read-only, so the existing document was reused as-is with no close/reopen. If it was already open but not confirmed read-only, this call fails with ASSEMBLY_ALREADY_OPEN_NOT_READONLY instead; this connector never closes or reopens a document it did not open itself.",
                "issues", issues,
                "safety", "The assembly was opened for reading only. Ordinary tools cannot save it. Scoped experiment tools require a separately configured and explicitly authorized test folder and still reject saving a read-only document.",
                "manufacturing_approved", false);
        }
        object DocumentDependencies(Dictionary<string, object> args)
        {
            string requestedPath = Catalog.LocalAnyDocumentPathText(args, "file_path");
            string verifiedPath = Program.RequireLocalFixedPath(requestedPath, true);
            object[] callArgs = { verifiedPath, false, false, false };
            object raw = Try("document_dependencies.api_call", delegate {
                return Call(app, "ISldWorks", "GetDocumentDependencies2", callArgs);
            });
            var dependencies = new List<object>();
            var arr = raw as Array;
            if (arr != null) foreach (object item in arr) dependencies.Add(Text(item));
            return Json.Obj("operation", "DOCUMENT_DEPENDENCIES", "connector_version", Program.Version,
                "file_path", verifiedPath,
                "dependencies", dependencies.ToArray(),
                "dependency_count", dependencies.Count,
                "api", "ISldWorks.GetDocumentDependencies2(Document, Traverseflag=false, Searchflag=false, AddReadOnlyInfo=false)",
                "api_call_status", raw != null ? "OK" : "UNKNOWN",
                "opens_document", false,
                "issues", issues,
                "note", "Raw file paths SOLIDWORKS reports as dependencies of file_path (what file_path itself references), read directly from the live API without opening file_path as the active document and without interpreting, filtering or resolving the result. api_call_status=UNKNOWN means the API call itself failed (see issues); an empty dependencies list is then not evidence of zero dependencies. This tool alone does not prove file_path is or is not a root assembly: that requires calling it once per other candidate assembly file in the relevant folder and checking whether file_path's own path text appears in THEIR returned dependencies list. Whether the returned array includes file_path itself as an element, and the exact ordering, are reported exactly as observed from the live API and are not assumed from SOLIDWORKS documentation.",
                "manufacturing_approved", false);
        }
        object OpenWorkspacePath(string filePath)
        {
            RequireWorkspacePath(filePath);
            return OpenLocalPath(filePath);
        }
        object OpenWorkspaceFile(Dictionary<string, object> args)
        {
            string root = Program.EnsureWorkspace();
            string fileName = Catalog.WorkspaceFileName(args);
            object result = OpenWorkspacePath(Path.Combine(root, fileName));
            return Json.Obj("operation", "OPENED_WORKSPACE_FILE", "connector_version", Program.Version,
                "file_path", Json.At(Json.Map(result), "path"), "document_type", Json.At(Json.Map(result), "document_type"),
                "open_errors", Json.At(Json.Map(result), "errors"), "open_warnings", Json.At(Json.Map(result), "warnings"),
                "open_status", Json.At(Json.Map(result), "open_status"),
                "open_status_note", Json.At(Json.Map(result), "open_status_note"),
                "workspace_path", root, "manufacturing_approved", false);
        }
        object OpenLocalFile(Dictionary<string, object> args)
        {
            string requestedPath = Catalog.LocalDocumentPathText(args, "file_path");
            string verifiedPath = Program.RequireLocalFixedPath(requestedPath, true);
            object result = OpenLocalPath(verifiedPath);
            return Json.Obj("operation", "OPENED_LOCAL_FILE", "connector_version", Program.Version,
                "file_path", Json.At(Json.Map(result), "path"),
                "document_type", Json.At(Json.Map(result), "document_type"),
                "open_errors", Json.At(Json.Map(result), "errors"),
                "open_warnings", Json.At(Json.Map(result), "warnings"),
                "open_status", Json.At(Json.Map(result), "open_status"),
                "open_status_note", Json.At(Json.Map(result), "open_status_note"),
                "inside_workspace", Program.IsWorkspacePath(verifiedPath),
                "local_fixed_disk_only", true, "network_paths_allowed", false,
                "manufacturing_approved", false);
        }
        object CopyActiveToWorkspace()
        {
            Document();
            if (kind != 1) throw new Fault("PART_REQUIRED", "Open a saved SLDPRT. Only parts can be copied into the controlled workspace.");
            if (string.IsNullOrWhiteSpace(path) || !File.Exists(path))
                throw new Fault("SAVED_PART_REQUIRED", "Save the source part manually before copying it into the workspace.");
            if (dirty != false) throw new Fault("CLEAN_SOURCE_REQUIRED", "A confirmed clean source is required before making a workspace copy.");
            string sourcePath = path, sourceTitle = title;
            Program.RequireLocalFixedPath(sourcePath, true);
            string destination = UniqueWorkspacePath(Path.GetFileNameWithoutExtension(sourcePath) + "_WORK", ".SLDPRT");
            bool copied = false;
            try
            {
                File.Copy(sourcePath, destination, false); copied = true;
                object openedResult = OpenWorkspacePath(destination);
                bool sourceUnchanged = string.Equals(Text(Call(model, "IModelDoc2", "GetTitle")), sourceTitle, StringComparison.Ordinal) &&
                    string.Equals(Text(Call(model, "IModelDoc2", "GetPathName")), sourcePath, StringComparison.OrdinalIgnoreCase) &&
                    Bool(Call(model, "IModelDoc2", "GetSaveFlag")) == false;
                if (!sourceUnchanged) throw new Fault("SOURCE_CHANGED", "The source document state changed while the workspace copy was opened.");
                return Json.Obj("operation", "COPIED_ACTIVE_PART_TO_WORKSPACE", "connector_version", Program.Version,
                    "source_path", sourcePath, "source_unchanged", true, "workspace_copy_path", destination,
                    "workspace_copy_active", true, "copy_method", "File.Copy + ISldWorks.OpenDoc6",
                    "external_references_audited", false,
                    "safety", "The local fixed-disk source file was read byte-for-byte and was not saved, edited or closed. Network and removable sources are rejected.",
                    "manufacturing_approved", false);
            }
            catch
            {
                if (copied)
                    try { if (File.Exists(destination)) File.Delete(destination); } catch { }
                throw;
            }
        }
        object SaveLocalDocumentCore(bool makeBackup)
        {
            if (makeBackup) Document();
            else RequireWriteTargetUnchanged();
            if (kind != 1 && kind != 3) throw new Fault("LOCAL_FILE_TYPE", "Only local SLDPRT and SLDDRW documents can be saved.");
            path = Program.RequireLocalFixedPath(path, true);
            RequireWritableDocument();
            string extension = Path.GetExtension(path);
            if (!string.Equals(extension, ".SLDPRT", StringComparison.OrdinalIgnoreCase) &&
                !string.Equals(extension, ".SLDDRW", StringComparison.OrdinalIgnoreCase))
                throw new Fault("LOCAL_FILE_TYPE", "Only local SLDPRT and SLDDRW documents can be saved.");
            string backupPath = makeBackup
                ? CreateLocalBackup(path, "_BEFORE_SAVE") : null;
            RequireWriteTargetUnchanged();
            bool drawingRebuilt = false;
            if (kind == 3)
            {
                // A drawing's displayed dimensions and views are only guaranteed current
                // after an explicit rebuild; unlike parts, no earlier step in this call
                // path already rebuilt it. Fail closed (backup retained) rather than save
                // a drawing that may not reflect its current referenced model state.
                if (!Convert.ToBoolean(Call(model, "IModelDoc2", "EditRebuild3")))
                    throw new Fault("DRAWING_REBUILD_FAILED", "The drawing did not rebuild cleanly; it was not saved. The backup is retained.");
                RequireWriteTargetUnchanged();
                drawingRebuilt = true;
            }
            int silent = EnumValue("swSaveAsOptions_e", "swSaveAsOptions_Silent");
            object[] saveArgs = { silent, 0, 0 };
            bool saved = Convert.ToBoolean(Call(model, "IModelDoc2", "Save3", saveArgs));
            int errors = Convert.ToInt32(saveArgs[1], CultureInfo.InvariantCulture);
            int warnings = Convert.ToInt32(saveArgs[2], CultureInfo.InvariantCulture);
            bool clean = !Convert.ToBoolean(Call(model, "IModelDoc2", "GetSaveFlag"));
            if (!saved || errors != 0 || !clean || !File.Exists(path))
                throw new Fault("SAVE_FAILED", "The local document was not saved cleanly. success=" + saved + ", errors=" + errors + ", warnings=" + warnings + ", clean=" + clean);
            return Json.Obj("operation", "SAVED_LOCAL_DOCUMENT", "connector_version", Program.Version,
                "file_path", path, "document_type", kind == 1 ? "PART" : "DRAWING", "api_success", saved,
                "errors", errors, "warnings", warnings, "backup_path", backupPath,
                "drawing_rebuilt_before_save", kind == 3 ? (object)drawingRebuilt : null,
                "inside_workspace", Program.IsWorkspacePath(path), "local_fixed_disk_only", true,
                "network_paths_allowed", false, "manufacturing_approved", false);
        }
        object SaveWorkspaceDocument()
        {
            return SaveLocalDocumentCore(true);
        }
        void RequireWriteTargetUnchanged()
        {
            // Retain the validated object; never replace it with a newly active document.
            object current = Get(app, "ISldWorks", "IActiveDoc2");
            if (model == null || !Object.ReferenceEquals(current, model) ||
                !string.Equals(Text(Call(model, "IModelDoc2", "GetPathName")), path, StringComparison.OrdinalIgnoreCase) ||
                !string.Equals(Text(Call(model, "IModelDoc2", "GetTitle")), title, StringComparison.Ordinal) ||
                Convert.ToInt32(Call(model, "IModelDoc2", "GetType"), CultureInfo.InvariantCulture) != kind)
                throw new Fault("DOCUMENT_CHANGED", "The validated write target is no longer active or its identity changed. Nothing else will be saved.");
            if (kind == 1 && (string.IsNullOrWhiteSpace(config) ||
                !string.Equals(ActiveConfigurationOf(model), config, StringComparison.Ordinal)))
                throw new Fault("CONFIGURATION_CHANGED", "The validated write configuration changed or could not be confirmed.");
        }
        void RequireWritableDocument()
        {
            RequireWriteTargetUnchanged();
            if (!dirty.HasValue)
                throw new Fault("DOCUMENT_STATE_UNKNOWN", "The document save flag is unavailable; writing is blocked.");
            object readOnly = Try("document.read_only", delegate { return Call(model, "IModelDoc2", "IsOpenedReadOnly"); });
            if (readOnly == null || Convert.ToBoolean(readOnly, CultureInfo.InvariantCulture))
                throw new Fault("DOCUMENT_NOT_WRITABLE", "The document is read-only or its access mode is unknown; writing is blocked.");
        }
        object SetWorkspaceProperties(Dictionary<string, object> args)
        {
            Document();
            if (kind != 1) throw new Fault("PART_REQUIRED", "Open a local SLDPRT before setting part properties or material.");
            path = Program.RequireLocalFixedPath(path, true);
            if (dirty != false) throw new Fault("CLEAN_LOCAL_PART_REQUIRED", "A confirmed clean source is required before changing local part properties.");
            RequireWritableDocument();
            string backupPath = CreateLocalBackup(path, "_BEFORE_PROPERTIES_CHANGE");
            var values = new NewPartProperties {
                Designation = Catalog.TextValue(args, "designation", false, 120),
                Name = Catalog.TextValue(args, "name", false, 120)
            };
            string materialName = Catalog.TextValue(args, "material", false, 40);
            if (materialName != null) materialName = "AISI 304";
            CheckUnchanged();
            object properties = ApplyNewPartProperties(model, values.Designation == null && values.Name == null ? null : values);
            object material = ApplyAndVerifyMaterial(model, materialName);
            if (!Convert.ToBoolean(Call(model, "IModelDoc2", "EditRebuild3")))
                throw new Fault("PROPERTY_REBUILD_FAILED", "The part did not rebuild after changing properties; it was not saved. The backup is retained.");
            object save = SaveLocalDocumentCore(false);
            return Json.Obj("operation", "UPDATED_LOCAL_PART_PROPERTIES", "connector_version", Program.Version,
                "file_path", path, "written_properties", properties, "material", material,
                "save", save, "backup_path", backupPath, "geometry_edit", false,
                "inside_workspace", Program.IsWorkspacePath(path), "local_fixed_disk_only", true,
                "network_paths_allowed", false, "manufacturing_approved", false);
        }
        double DimensionSystemValue(object dimension)
        {
            int thisConfiguration = EnumValue("swInConfigurationOpts_e", "swThisConfiguration");
            var values = Call(dimension, "IDimension", "GetSystemValue3", thisConfiguration, null) as Array;
            if (values == null || values.Length < 1)
                throw new Fault("PARAMETER_VALUE_UNAVAILABLE", "SOLIDWORKS did not return the dimension value for the active configuration.");
            double value = Convert.ToDouble(values.GetValue(0), CultureInfo.InvariantCulture);
            if (double.IsNaN(value) || double.IsInfinity(value))
                throw new Fault("PARAMETER_VALUE_INVALID", "SOLIDWORKS returned an invalid dimension value.");
            return value;
        }
        static bool ConnectorParameterName(string name)
        {
            return !string.IsNullOrEmpty(name) && name.StartsWith("AI_", StringComparison.Ordinal) && name.Length <= 80;
        }
        internal static bool IsConnectorParameterName(string name) { return ConnectorParameterName(name); }
        IEnumerable<string> ConnectorFeatureParameterCandidates(string featureType)
        {
            // Display dimensions are not guaranteed to remain enumerable through
            // IFeature.GetFirstDisplayDimension after a save/reopen.  Connector-created
            // dimensions have a deliberately small, documented namespace, so probe
            // those names directly through IFeature.Parameter as a second API path.
            if (EditableFeatureType(featureType))
            {
                // IDimension.Name can change to AI_Thickness while the feature-local
                // lookup key remains D1. Probe a small native key range and accept a
                // result only after reading and validating its real Name/FullName.
                for (int i = 1; i <= 16; i++) yield return "D" + i;
                yield return "AI_Thickness";
            }
            if (featureType == "ProfileFeature" || featureType == "Sketch")
            {
                yield return "AI_Length";
                yield return "AI_Width";
                for (int i = 1; i <= 64; i++)
                {
                    yield return "AI_Hole_Diameter_" + i;
                    yield return "AI_Hole_Offset_X_" + i;
                    yield return "AI_Hole_Offset_Y_" + i;
                }
            }
        }
        void AppendParameterRow(List<object> items, List<object> readIssues, HashSet<string> names,
            object dimension, string featureName, string featureType, bool localFixed, string sourceApi)
        {
            if (dimension == null) return;
            try
            {
                string name = Text(Get(dimension, "IDimension", "Name"));
                string fullName = Text(Get(dimension, "IDimension", "FullName"));
                if (string.IsNullOrWhiteSpace(fullName) || !names.Add(fullName)) return;
                bool readOnly = Convert.ToBoolean(Get(dimension, "IDimension", "ReadOnly"));
                int drivingValue = EnumValue("swDimensionDrivenState_e", "swDimensionDriving");
                int drivenState = Convert.ToInt32(Get(dimension, "IDimension", "DrivenState"), CultureInfo.InvariantCulture);
                double systemValue = DimensionSystemValue(dimension);
                bool managed = ConnectorParameterName(name);
                int dimensionType = DimensionTypeCode(dimension);
                string dimensionTypeName = DimensionTypeName(dimensionType);
                bool linear = VerifiedLinearDimension(dimensionType);
                items.Add(Json.Obj("name", name, "full_name", fullName, "feature_name", featureName,
                    "feature_type", featureType, "dimension_type_code", dimensionType,
                    "dimension_type", dimensionTypeName,
                    "dimension_type_enum", "swDimensionParamType_e",
                    "dimension_kind", linear ? "LINEAR" : "UNSUPPORTED_NON_LINEAR",
                    "system_value_si", systemValue,
                    "value_mm", linear ? (object)(systemValue * 1000.0) : null,
                    "read_only", readOnly, "driving", drivenState == drivingValue,
                    "inventory_source", sourceApi,
                    "editable_by_connector", localFixed && managed && linear && !readOnly && drivenState == drivingValue));
            }
            catch (Exception ex)
            {
                readIssues.Add(Json.Obj("code", "DIMENSION_READ_FAILED", "feature_name", featureName,
                    "source_api", sourceApi, "message", Program.Unwrap(ex)));
            }
        }
        object ParametersData()
        {
            if (kind != 1) throw new Fault("PART_REQUIRED", "sw_parameters requires an active SLDPRT part.");
            bool localFixed = !string.IsNullOrWhiteSpace(path) && Program.IsLocalFixedPath(path, true);
            var items = new List<object>();
            var issues = new List<object>();
            var names = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
            object feature = Call(model, "IModelDoc2", "IFirstFeature");
            int featureGuard = 0;
            while (feature != null && featureGuard++ < 1000)
            {
                string featureName = Text(Get(feature, "IFeature", "Name"));
                string featureType = Text(Call(feature, "IFeature", "GetTypeName2"));
                object displayDimension = Call(feature, "IFeature", "GetFirstDisplayDimension");
                int dimensionGuard = 0;
                while (displayDimension != null && dimensionGuard++ < 1000)
                {
                    object dimension = null;
                    try { dimension = Call(displayDimension, "IDisplayDimension", "GetDimension2", 0); }
                    catch (Exception ex)
                    {
                        issues.Add(Json.Obj("code", "DIMENSION_READ_FAILED", "feature_name", featureName,
                            "source_api", "IFeature.GetFirstDisplayDimension", "message", Program.Unwrap(ex)));
                    }
                    AppendParameterRow(items, issues, names, dimension, featureName, featureType, localFixed,
                        "IFeature.GetFirstDisplayDimension");
                    displayDimension = Call(feature, "IFeature", "GetNextDisplayDimension", displayDimension);
                }
                if (dimensionGuard >= 1000)
                    throw new Fault("PARAMETER_TRAVERSAL_FAILED", "Display-dimension traversal exceeded the safety limit.");
                foreach (string candidate in ConnectorFeatureParameterCandidates(featureType))
                {
                    object direct = null;
                    try { direct = Call(feature, "IFeature", "Parameter", candidate); }
                    catch { continue; }
                    AppendParameterRow(items, issues, names, direct, featureName, featureType, localFixed,
                        "IFeature.Parameter:" + candidate);
                }
                if (EditableFeatureType(featureType))
                {
                    foreach (string nativeName in new[] { "D1", "AI_Thickness" })
                    {
                        string modelKey = nativeName + "@" + featureName;
                        object direct = null;
                        try { direct = Call(model, "IModelDoc2", "Parameter", modelKey); }
                        catch { continue; }
                        AppendParameterRow(items, issues, names, direct, featureName, featureType, localFixed,
                            "IModelDoc2.Parameter:" + modelKey);
                    }
                }
                feature = Call(feature, "IFeature", "GetNextFeature");
            }
            if (featureGuard >= 1000)
                throw new Fault("PARAMETER_TRAVERSAL_FAILED", "Feature traversal exceeded the safety limit.");
            return Json.Obj("items", items.ToArray(), "total", items.Count, "issues", issues.ToArray(),
                "partial", issues.Count > 0, "workspace_part", Program.IsWorkspacePath(path),
                "local_fixed_disk_part", localFixed, "network_paths_allowed", false,
                "editable_prefix", "AI_", "configuration", config,
                "scope", "Dimensions are inventoried from display dimensions plus direct IFeature.Parameter lookup for connector-created AI_* dimensions that SOLIDWORKS may hide after save/reopen. sw_features consumes this same inventory.");
        }
        internal static bool EditableFeatureType(string featureType)
        {
            return featureType == "Extrusion" || featureType == "Boss" || featureType == "Cut" || featureType == "HoleWzd" ||
                featureType == "Chamfer" || featureType == "Fillet";
        }
        bool FeatureSuppressed(object feature)
        {
            int thisConfiguration = EnumValue("swInConfigurationOpts_e", "swThisConfiguration");
            object value = Call(feature, "IFeature", "IsSuppressed2", thisConfiguration, null);
            var states = value as Array;
            if (states != null)
            {
                if (states.Length < 1) throw new Fault("FEATURE_SUPPRESSION_UNKNOWN", "SOLIDWORKS returned no suppression state for the active configuration.");
                return Convert.ToBoolean(states.GetValue(0), CultureInfo.InvariantCulture);
            }
            if (value == null) throw new Fault("FEATURE_SUPPRESSION_UNKNOWN", "SOLIDWORKS returned no suppression state.");
            return Convert.ToBoolean(value, CultureInfo.InvariantCulture);
        }
        int DimensionTypeCode(object dimension)
        {
            return Convert.ToInt32(Call(dimension, "IDimension", "GetType"), CultureInfo.InvariantCulture);
        }
        string DimensionTypeName(int code)
        {
            if (swconst == null) return null;
            // IDimension.GetType uses the parameter enum, not IDisplayDimension.Type2's enum.
            Type type = swconst.GetType("SolidWorks.Interop.swconst.swDimensionParamType_e", false);
            return type == null || !type.IsEnum ? null : Enum.GetName(type, code);
        }
        internal static bool LinearDimensionTypeName(string name)
        {
            return name == "swDimensionParamTypeDoubleLinear";
        }
        bool IsLinearDimension(object dimension)
        {
            int code = DimensionTypeCode(dimension);
            return LinearDimensionTypeName(DimensionTypeName(code));
        }
        bool VerifiedLinearDimension(int code)
        {
            return LinearDimensionTypeName(DimensionTypeName(code));
        }
        static bool DimensionOwnedByFeature(string fullName, string featureName)
        {
            if (string.IsNullOrWhiteSpace(fullName) || string.IsNullOrWhiteSpace(featureName)) return false;
            string[] parts = fullName.Split('@');
            return parts.Length >= 2 && string.Equals(parts[1], featureName, StringComparison.Ordinal);
        }
        object FeatureDimensionRow(object displayDimension, string featureName, string featureType,
            bool? suppressed, bool localFixed)
        {
            object dimension = Call(displayDimension, "IDisplayDimension", "GetDimension2", 0);
            if (dimension == null) throw new Fault("DIMENSION_UNAVAILABLE", "SOLIDWORKS did not return the feature dimension.");
            string name = Text(Get(dimension, "IDimension", "Name"));
            string fullName = Text(Get(dimension, "IDimension", "FullName"));
            bool readOnly = Convert.ToBoolean(Get(dimension, "IDimension", "ReadOnly"));
            int drivingValue = EnumValue("swDimensionDrivenState_e", "swDimensionDriving");
            int drivenState = Convert.ToInt32(Get(dimension, "IDimension", "DrivenState"), CultureInfo.InvariantCulture);
            int dimensionType = DimensionTypeCode(dimension);
            string dimensionTypeName = DimensionTypeName(dimensionType);
            bool linear = VerifiedLinearDimension(dimensionType);
            double systemValue = DimensionSystemValue(dimension);
            bool editable = localFixed && EditableFeatureType(featureType) && suppressed == false &&
                linear && !readOnly && drivenState == drivingValue && DimensionOwnedByFeature(fullName, featureName);
            return Json.Obj("name", name, "full_name", fullName, "feature_name", featureName,
                "feature_type", featureType, "dimension_type_code", dimensionType,
                "dimension_type", dimensionTypeName,
                "dimension_type_enum", "swDimensionParamType_e",
                "dimension_kind", linear ? "LINEAR" : "UNSUPPORTED_NON_LINEAR",
                "system_value_si", systemValue, "value_mm", linear ? (object)(systemValue * 1000.0) : null,
                "read_only", readOnly, "driving", drivenState == drivingValue,
                "editable_by_feature_tool", editable);
        }
        object FeaturesData(Dictionary<string, object> args)
        {
            if (kind != 1) throw new Fault("PART_REQUIRED", "sw_features requires an active SLDPRT part.");
            int offset = Catalog.Number(args, "offset", 0, 0, 100000);
            int limit = Catalog.Number(args, "limit", 25, 1, 100);
            bool localFixed = !string.IsNullOrWhiteSpace(path) && Program.IsLocalFixedPath(path, true);
            var rows = new List<object>();
            var readIssues = new List<object>();
            var parameterResult = Json.Map(ParametersData());
            var allDimensions = Json.At(parameterResult, "items") as Array;
            var parameterIssues = Json.At(parameterResult, "issues") as Array;
            if (parameterIssues != null)
                foreach (object issue in parameterIssues) readIssues.Add(issue);
            object feature = Call(model, "IModelDoc2", "IFirstFeature");
            int index = 0, guard = 0;
            while (feature != null && guard++ < 2000)
            {
                if (index >= offset && rows.Count < limit)
                {
                    string featureName = Text(Get(feature, "IFeature", "Name"));
                    string featureType = Text(Call(feature, "IFeature", "GetTypeName2"));
                    bool? suppressed = null;
                    try { suppressed = FeatureSuppressed(feature); }
                    catch (Exception ex)
                    {
                        readIssues.Add(Json.Obj("code", "FEATURE_SUPPRESSION_READ_FAILED",
                            "feature_name", featureName, "message", ex.Message));
                    }
                    var dimensions = new List<object>();
                    if (allDimensions != null)
                    {
                        foreach (object dimensionValue in allDimensions)
                        {
                            var sourceDimension = Json.Map(dimensionValue);
                            if (sourceDimension == null || !string.Equals(Text(Json.At(sourceDimension, "feature_name")),
                                featureName, StringComparison.Ordinal)) continue;
                            var dimension = new Dictionary<string, object>(sourceDimension);
                            bool linear = string.Equals(Text(Json.At(dimension, "dimension_kind")), "LINEAR", StringComparison.Ordinal);
                            bool readOnly = Convert.ToBoolean(Json.At(dimension, "read_only", true), CultureInfo.InvariantCulture);
                            bool driving = Convert.ToBoolean(Json.At(dimension, "driving", false), CultureInfo.InvariantCulture);
                            dimension["editable_by_feature_tool"] = localFixed && EditableFeatureType(featureType) &&
                                suppressed == false && linear && !readOnly && driving &&
                                DimensionOwnedByFeature(Text(Json.At(dimension, "full_name")), featureName);
                            dimensions.Add(dimension);
                        }
                    }
                    rows.Add(Json.Obj("index", index, "feature_name", featureName, "feature_type", featureType,
                        "suppressed", suppressed, "supported_for_dimension_edit", EditableFeatureType(featureType),
                        "dimensions", dimensions.ToArray(), "dimension_count", dimensions.Count));
                }
                index++;
                feature = Call(feature, "IFeature", "GetNextFeature");
            }
            if (guard >= 2000) throw new Fault("FEATURE_TRAVERSAL_FAILED", "Feature traversal exceeded the safety limit.");
            return Json.Obj("items", rows.ToArray(), "offset", offset, "limit", limit, "total", index,
                "truncated", offset + rows.Count < index, "issues", readIssues.ToArray(),
                "partial", readIssues.Count > 0, "configuration", config,
                "local_fixed_disk_part", localFixed, "network_paths_allowed", false,
                "supported_feature_types", new[] { "Extrusion", "Boss", "Cut", "HoleWzd", "Chamfer", "Fillet" },
                "scope", "Top-level feature inventory. Only directly owned linear driving dimensions marked editable_by_feature_tool=true are eligible. Sketch dimensions, angles, suppressed features and unknown feature types are read-only.");
        }
        object FindExactFeature(string requestedName, out string featureType)
        {
            object match = null;
            featureType = null;
            int count = 0, guard = 0;
            object feature = Call(model, "IModelDoc2", "IFirstFeature");
            while (feature != null && guard++ < 2000)
            {
                string name = Text(Get(feature, "IFeature", "Name"));
                if (string.Equals(name, requestedName, StringComparison.Ordinal))
                {
                    match = feature;
                    featureType = Text(Call(feature, "IFeature", "GetTypeName2"));
                    count++;
                }
                feature = Call(feature, "IFeature", "GetNextFeature");
            }
            if (guard >= 2000) throw new Fault("FEATURE_TRAVERSAL_FAILED", "Feature traversal exceeded the safety limit.");
            if (count == 0) throw new Fault("FEATURE_NOT_FOUND", "The exact feature_name was not found. Read sw_features again.");
            if (count != 1) throw new Fault("FEATURE_AMBIGUOUS", "The feature_name is not unique in the active feature tree.");
            return match;
        }
        ResolvedManagedParameter ResolveOwnedFeatureDimension(object feature, ManagedParameterChange request)
        {
            string ownerName = Text(Get(feature, "IFeature", "Name"));
            if (!DimensionOwnedByFeature(request.FullName, ownerName))
                throw new Fault("FEATURE_DIMENSION_NOT_OWNED", "The dimension full_name does not identify the selected feature as its direct owner.");
            object found = null;
            int count = 0, guard = 0;
            object displayDimension = Call(feature, "IFeature", "GetFirstDisplayDimension");
            while (displayDimension != null && guard++ < 256)
            {
                object dimension = Call(displayDimension, "IDisplayDimension", "GetDimension2", 0);
                if (dimension != null && string.Equals(Text(Get(dimension, "IDimension", "FullName")),
                    request.FullName, StringComparison.Ordinal)) { found = dimension; count++; }
                displayDimension = Call(feature, "IFeature", "GetNextDisplayDimension", displayDimension);
            }
            if (guard >= 256) throw new Fault("FEATURE_TRAVERSAL_FAILED", "Feature dimension traversal exceeded the safety limit.");
            if (count == 0)
            {
                object modelDimension = null;
                try { modelDimension = Call(model, "IModelDoc2", "Parameter", request.FullName); } catch { }
                if (modelDimension != null && string.Equals(Text(Get(modelDimension, "IDimension", "FullName")),
                    request.FullName, StringComparison.OrdinalIgnoreCase))
                {
                    found = modelDimension;
                    count = 1;
                }
            }
            if (count == 0)
            {
                int separator = request.FullName.IndexOf('@');
                string directName = separator > 0 ? request.FullName.Substring(0, separator) : request.FullName;
                var lookupNames = new List<string> { directName };
                for (int i = 1; i <= 16; i++) lookupNames.Add("D" + i);
                foreach (string lookupName in lookupNames)
                {
                    object direct = null;
                    try { direct = Call(feature, "IFeature", "Parameter", lookupName); } catch { continue; }
                    if (direct != null && string.Equals(Text(Get(direct, "IDimension", "FullName")),
                        request.FullName, StringComparison.OrdinalIgnoreCase))
                    {
                        found = direct;
                        count = 1;
                        break;
                    }
                }
            }
            if (count == 0) throw new Fault("FEATURE_DIMENSION_NOT_FOUND", "The exact full_name is not owned directly by the selected feature: " + request.FullName);
            if (count != 1) throw new Fault("FEATURE_DIMENSION_AMBIGUOUS", "The requested dimension identity is not unique inside the feature.");
            string foundName = Text(Get(found, "IDimension", "Name"));
            if (!DimensionOwnedByFeature(Text(Get(found, "IDimension", "FullName")), ownerName))
                throw new Fault("FEATURE_DIMENSION_NOT_OWNED", "SOLIDWORKS returned a dimension owned by another feature.");
            if (!VerifiedLinearDimension(DimensionTypeCode(found)))
                throw new Fault("FEATURE_DIMENSION_NOT_LINEAR", "Only verified linear dimensions measured in millimetres can be changed.");
            if (Convert.ToBoolean(Get(found, "IDimension", "ReadOnly")))
                throw new Fault("FEATURE_DIMENSION_READ_ONLY", "The requested feature dimension is read-only.");
            int drivingValue = EnumValue("swDimensionDrivenState_e", "swDimensionDriving");
            int drivenState = Convert.ToInt32(Get(found, "IDimension", "DrivenState"), CultureInfo.InvariantCulture);
            if (drivenState != drivingValue) throw new Fault("FEATURE_DIMENSION_NOT_DRIVING", "Only driving feature dimensions can be changed.");
            double originalM = DimensionSystemValue(found);
            double originalMm = originalM * 1000.0;
            double toleranceMm = Math.Max(0.001, Math.Abs(originalMm) * 1e-6);
            if (Math.Abs(originalMm - request.ExpectedMm) > toleranceMm)
                throw new Fault("FEATURE_DIMENSION_STALE_VALUE", "The current value differs from expected_current_mm. Read sw_features again.");
            return new ResolvedManagedParameter { Request = request, Dimension = found,
                Name = foundName,
                FullName = Text(Get(found, "IDimension", "FullName")), OriginalM = originalM };
        }
        int SolidBodyCount(object target)
        {
            int solidBody = EnumValue("swBodyType_e", "swSolidBody");
            var bodies = Call(target, "IPartDoc", "GetBodies2", solidBody, false) as Array;
            return bodies == null ? 0 : bodies.Length;
        }

        sealed class ResolvedManagedParameter
        {
            internal ManagedParameterChange Request;
            internal object Dimension;
            internal string Name;
            internal string FullName;
            internal double OriginalM;
        }

        ResolvedManagedParameter ResolveManagedParameter(ManagedParameterChange request)
        {
            // In the SOLIDWORKS 2026 interop this indexed COM member is exposed
            // as IModelDoc2.Parameter(string), not as a PropertyInfo indexer.
            object dimension = Call(model, "IModelDoc2", "Parameter", request.FullName);
            if (dimension == null)
                throw new Fault("PARAMETER_NOT_FOUND", "The exact parameter full_name was not found: " + request.FullName);
            string actualFullName = Text(Get(dimension, "IDimension", "FullName"));
            string parameterName = Text(Get(dimension, "IDimension", "Name"));
            if (!string.Equals(actualFullName, request.FullName, StringComparison.OrdinalIgnoreCase))
                throw new Fault("PARAMETER_IDENTITY_MISMATCH", "SOLIDWORKS returned a different parameter than requested: " + request.FullName);
            if (!ConnectorParameterName(parameterName))
                throw new Fault("PARAMETER_NOT_MANAGED", "Only AI_* dimensions created by this connector can be changed: " + request.FullName);
            int dimensionType = DimensionTypeCode(dimension);
            if (!VerifiedLinearDimension(dimensionType))
                throw new Fault("PARAMETER_NOT_LINEAR", "Only verified linear AI_* dimensions can be changed in millimetres.");
            if (Convert.ToBoolean(Get(dimension, "IDimension", "ReadOnly")))
                throw new Fault("PARAMETER_READ_ONLY", "The requested parameter is read-only: " + request.FullName);
            int drivingValue = EnumValue("swDimensionDrivenState_e", "swDimensionDriving");
            int drivenState = Convert.ToInt32(Get(dimension, "IDimension", "DrivenState"), CultureInfo.InvariantCulture);
            if (drivenState != drivingValue)
                throw new Fault("PARAMETER_NOT_DRIVING", "Only driving dimensions can be changed: " + request.FullName);
            double originalM = DimensionSystemValue(dimension);
            double originalMm = originalM * 1000.0;
            double toleranceMm = Math.Max(0.001, Math.Abs(originalMm) * 1e-6);
            if (Math.Abs(originalMm - request.ExpectedMm) > toleranceMm)
                throw new Fault("PARAMETER_STALE_VALUE", "The current value differs from expected_current_mm for " + request.FullName + ". Read sw_parameters again.");
            if (Math.Abs(request.RequestedMm - originalMm) <= toleranceMm)
                throw new Fault("PARAMETER_UNCHANGED", "new_value_mm must differ from the current value: " + request.FullName);
            return new ResolvedManagedParameter { Request = request, Dimension = dimension,
                Name = parameterName, FullName = actualFullName, OriginalM = originalM };
        }

        object SetWorkspaceParametersCore(List<ManagedParameterChange> requests, bool single, bool makeBackup)
        {
            if (makeBackup) Document();
            else RequireWriteTargetUnchanged();
            if (kind != 1) throw new Fault("PART_REQUIRED", "Open a local SLDPRT before changing connector parameters. The active document is not a part.");
            path = Program.RequireLocalFixedPath(path, true);
            if (dirty != false) throw new Fault("CLEAN_LOCAL_PART_REQUIRED", "A confirmed clean source is required before changing connector parameters.");
            RequireWritableDocument();
            var resolved = new List<ResolvedManagedParameter>();
            foreach (ManagedParameterChange request in requests) resolved.Add(ResolveManagedParameter(request));

            string sourcePath = path;
            string backupPath = null;
            if (makeBackup)
            {
                backupPath = CreateLocalBackup(path, "_BEFORE_PARAMETERS_CHANGE");
            }
            double beforeVolume = VolumeOf(model);
            bool committed = false;
            try
            {
                int thisConfiguration = EnumValue("swSetValueInConfiguration_e", "swSetValue_InThisConfiguration");
                var setStatuses = new List<int>();
                foreach (ResolvedManagedParameter item in resolved)
                {
                    RequireWriteTargetUnchanged();
                    int status = Convert.ToInt32(Call(item.Dimension, "IDimension", "SetSystemValue3",
                        item.Request.RequestedMm / 1000.0, thisConfiguration, null), CultureInfo.InvariantCulture);
                    setStatuses.Add(status);
                    if (status != 0)
                        throw new Fault("PARAMETER_SET_FAILED", "SOLIDWORKS rejected " + item.FullName + ". status=" + status);
                }
                RequireWriteTargetUnchanged();
                bool rebuilt = Convert.ToBoolean(Call(model, "IModelDoc2", "EditRebuild3"));
                var results = new List<object>();
                for (int i = 0; i < resolved.Count; i++)
                {
                    ResolvedManagedParameter item = resolved[i];
                    double actualMm = DimensionSystemValue(item.Dimension) * 1000.0;
                    double toleranceMm = Math.Max(0.001, Math.Abs(item.Request.RequestedMm) * 1e-6);
                    if (Math.Abs(actualMm - item.Request.RequestedMm) > toleranceMm)
                        throw new Fault("PARAMETER_VALUE_MISMATCH", "SOLIDWORKS did not preserve the requested value for " + item.FullName);
                    results.Add(Json.Obj("parameter_name", item.Name, "parameter_full_name", item.FullName,
                        "before_mm", item.OriginalM * 1000.0, "requested_mm", item.Request.RequestedMm,
                        "actual_mm", actualMm, "set_status", setStatuses[i], "value_tolerance_mm", toleranceMm));
                }
                int bodies = SolidBodyCount(model);
                double afterVolume = VolumeOf(model);
                if (!rebuilt || bodies != 1 || afterVolume <= 0.0)
                    throw new Fault("PARAMETER_VERIFICATION_FAILED", "Rebuild or geometric verification failed after changing the parameters.");
                object save = SaveLocalDocumentCore(false);
                committed = true;
                var response = Json.Obj("operation", single ? "UPDATED_WORKSPACE_PARAMETER" : "UPDATED_WORKSPACE_PARAMETERS",
                    "connector_version", Program.Version, "file_path", sourcePath, "backup_path", backupPath,
                    "configuration", config, "change_count", results.Count, "changes", results.ToArray(),
                    "verification", Json.Obj("status", "PASS", "rebuilt", rebuilt,
                        "solid_body_count", bodies, "volume_before_m3", beforeVolume,
                        "volume_after_m3", afterVolume, "all_requested_values_confirmed", true),
                    "save", save, "inside_workspace", Program.IsWorkspacePath(sourcePath),
                    "local_fixed_disk_only", true, "network_paths_allowed", false,
                    "manufacturing_approved", false);
                if (single)
                {
                    var first = Json.Map(results[0]);
                    foreach (string key in new[] { "parameter_name", "parameter_full_name", "before_mm",
                        "requested_mm", "actual_mm", "set_status" }) response.Add(key, first[key]);
                }
                return response;
            }
            finally
            {
                if (!committed)
                {
                    try
                    {
                        int thisConfiguration = EnumValue("swSetValueInConfiguration_e", "swSetValue_InThisConfiguration");
                        foreach (ResolvedManagedParameter item in resolved)
                        {
                            RequireWriteTargetUnchanged();
                            Call(item.Dimension, "IDimension", "SetSystemValue3", item.OriginalM, thisConfiguration, null);
                        }
                        RequireWriteTargetUnchanged();
                        Call(model, "IModelDoc2", "EditRebuild3");
                    }
                    catch { }
                }
            }
        }
        object SetWorkspaceParameter(Dictionary<string, object> args)
        {
            var request = new ManagedParameterChange {
                FullName = Catalog.TextValue(args, "full_name", true, 240),
                ExpectedMm = Catalog.Real(args, "expected_current_mm", 0.01, 2000.0),
                RequestedMm = Catalog.Real(args, "new_value_mm", 0.01, 2000.0)
            };
            return SetWorkspaceParametersCore(new List<ManagedParameterChange> { request }, true, true);
        }
        object SetWorkspaceParameters(Dictionary<string, object> args)
        {
            return SetWorkspaceParametersCore(ManagedParameterChange.ParseMany(args), false, true);
        }
        object SetFeatureDimensions(Dictionary<string, object> args)
        {
            Document();
            if (kind != 1) throw new Fault("PART_REQUIRED", "Open a local SLDPRT before changing feature dimensions.");
            path = Program.RequireLocalFixedPath(path, true);
            if (dirty != false) throw new Fault("CLEAN_LOCAL_PART_REQUIRED", "A confirmed clean source is required before changing feature dimensions.");
            RequireWritableDocument();
            string requestedFeatureName = Catalog.TextValue(args, "feature_name", true, 240);
            string expectedFeatureType = Catalog.TextValue(args, "expected_feature_type", true, 120);
            if (!EditableFeatureType(expectedFeatureType))
                throw new Fault("FEATURE_TYPE_NOT_SUPPORTED", "Only Extrusion, Boss, Cut, HoleWzd, Chamfer and Fillet dimensions are supported in this version.");
            string actualFeatureType;
            object feature = FindExactFeature(requestedFeatureName, out actualFeatureType);
            if (!string.Equals(actualFeatureType, expectedFeatureType, StringComparison.Ordinal))
                throw new Fault("FEATURE_TYPE_STALE", "The current feature type differs from expected_feature_type. Read sw_features again.");
            if (FeatureSuppressed(feature))
                throw new Fault("FEATURE_SUPPRESSED", "A suppressed feature cannot be changed.");
            var requests = ManagedParameterChange.ParseMany(args);
            var resolved = new List<ResolvedManagedParameter>();
            foreach (ManagedParameterChange request in requests)
                resolved.Add(ResolveOwnedFeatureDimension(feature, request));

            string sourcePath = path;
            string sourceHashBefore = FileSha256(sourcePath);
            string backupPath = CreateLocalBackup(sourcePath, "_BEFORE_FEATURE_CHANGE");
            int bodiesBefore = SolidBodyCount(model);
            double volumeBefore = VolumeOf(model);
            if (bodiesBefore < 1) throw new Fault("FEATURE_GEOMETRY_INVALID", "The source part has no solid body.");
            bool committed = false;
            try
            {
                int thisConfiguration = EnumValue("swSetValueInConfiguration_e", "swSetValue_InThisConfiguration");
                var setStatuses = new List<int>();
                foreach (ResolvedManagedParameter item in resolved)
                {
                    RequireWriteTargetUnchanged();
                    int status = Convert.ToInt32(Call(item.Dimension, "IDimension", "SetSystemValue3",
                        item.Request.RequestedMm / 1000.0, thisConfiguration, null), CultureInfo.InvariantCulture);
                    setStatuses.Add(status);
                    if (status != 0) throw new Fault("FEATURE_DIMENSION_SET_FAILED",
                        "SOLIDWORKS rejected " + item.FullName + ". status=" + status);
                }
                bool rebuilt = Convert.ToBoolean(Call(model, "IModelDoc2", "EditRebuild3"));
                RequireWriteTargetUnchanged();
                if (!rebuilt) throw new Fault("FEATURE_REBUILD_FAILED", "SOLIDWORKS did not rebuild the part after the requested feature change.");
                string verifiedFeatureType;
                object verifiedFeature = FindExactFeature(requestedFeatureName, out verifiedFeatureType);
                if (!string.Equals(verifiedFeatureType, expectedFeatureType, StringComparison.Ordinal) || FeatureSuppressed(verifiedFeature))
                    throw new Fault("FEATURE_IDENTITY_CHANGED", "The selected feature identity or suppression state changed after rebuild.");
                var results = new List<object>();
                for (int i = 0; i < resolved.Count; i++)
                {
                    ResolvedManagedParameter item = resolved[i];
                    double actualMm = DimensionSystemValue(item.Dimension) * 1000.0;
                    double toleranceMm = Math.Max(0.001, Math.Abs(item.Request.RequestedMm) * 1e-6);
                    if (Math.Abs(actualMm - item.Request.RequestedMm) > toleranceMm)
                        throw new Fault("FEATURE_DIMENSION_VALUE_MISMATCH", "SOLIDWORKS did not preserve the requested value for " + item.FullName);
                    results.Add(Json.Obj("name", item.Name, "full_name", item.FullName,
                        "before_mm", item.OriginalM * 1000.0, "requested_mm", item.Request.RequestedMm,
                        "actual_mm", actualMm, "set_status", setStatuses[i], "tolerance_mm", toleranceMm));
                }
                int bodiesAfter = SolidBodyCount(model);
                double volumeAfter = VolumeOf(model);
                if (bodiesAfter != bodiesBefore || bodiesAfter < 1 || volumeAfter <= 0.0)
                    throw new Fault("FEATURE_GEOMETRY_INVALID", "Solid-body count changed or final volume is invalid after the feature edit.");
                object save = SaveLocalDocumentCore(false);
                string sourceHashAfter = FileSha256(sourcePath);
                if (string.Equals(sourceHashAfter, sourceHashBefore, StringComparison.Ordinal))
                    throw new Fault("FEATURE_FILE_UNCHANGED", "The saved file bytes did not change after the requested feature edit.");
                committed = true;
                return Json.Obj("operation", "UPDATED_EXISTING_FEATURE_DIMENSIONS",
                    "connector_version", Program.Version, "file_path", sourcePath,
                    "backup_path", backupPath, "source_sha256_before", sourceHashBefore,
                    "source_sha256_after", sourceHashAfter, "feature_name", requestedFeatureName,
                    "feature_type", actualFeatureType, "configuration", config,
                    "change_count", results.Count, "changes", results.ToArray(),
                    "verification", Json.Obj("status", "PASS", "rebuilt", true,
                        "feature_identity_confirmed", true, "feature_not_suppressed", true,
                        "solid_body_count_before", bodiesBefore, "solid_body_count_after", bodiesAfter,
                        "volume_before_m3", volumeBefore, "volume_after_m3", volumeAfter,
                        "all_requested_values_confirmed", true),
                    "save", save, "inside_workspace", Program.IsWorkspacePath(sourcePath),
                    "local_fixed_disk_only", true, "network_paths_allowed", false,
                    "manufacturing_approved", false);
            }
            finally
            {
                if (!committed)
                {
                    try
                    {
                        int thisConfiguration = EnumValue("swSetValueInConfiguration_e", "swSetValue_InThisConfiguration");
                        foreach (ResolvedManagedParameter item in resolved)
                        {
                            RequireWriteTargetUnchanged();
                            Call(item.Dimension, "IDimension", "SetSystemValue3", item.OriginalM, thisConfiguration, null);
                        }
                        RequireWriteTargetUnchanged();
                        Call(model, "IModelDoc2", "EditRebuild3");
                    }
                    catch { }
                }
            }
        }
        internal static bool ValidGlobalVariableName(string name)
        {
            if (string.IsNullOrEmpty(name) || name.Length > 64) return false;
            char first = name[0];
            if (first != '_' && !(first >= 'A' && first <= 'Z') && !(first >= 'a' && first <= 'z')) return false;
            for (int i = 1; i < name.Length; i++)
            {
                char c = name[i];
                bool ok = c == '_' || (c >= 'A' && c <= 'Z') || (c >= 'a' && c <= 'z') || (c >= '0' && c <= '9');
                if (!ok) return false;
            }
            return true;
        }
        static string ParseEquationLhs(string equationText)
        {
            if (string.IsNullOrEmpty(equationText)) return null;
            int first = equationText.IndexOf('"');
            if (first < 0) return null;
            int second = equationText.IndexOf('"', first + 1);
            if (second <= first) return null;
            return equationText.Substring(first + 1, second - first - 1);
        }
        // Replaces one existing owned linear driving dimension's literal number with a NEW
        // named IEquationMgr global variable: "variable_name" = value_mm, then makes the
        // dimension's own equation reference that variable instead of holding a bare number.
        // This is the direct connector implementation of the explicit Dmitry Alexandrovich
        // brief ("подменить числовые значения на параметрические значения... переменная"):
        // the point is not necessarily to change the number (value_mm may equal
        // expected_current_mm) but to make it a named, reusable variable. Reuses exactly the
        // same feature/dimension gating as sw_set_feature_dimensions; adds one duplicate-name
        // check the shared resolver does not already cover, since an equation-driven
        // dimension can still report DrivenState=Driving.
        object SetGlobalVariable(Dictionary<string, object> args)
        {
            Document();
            if (kind != 1) throw new Fault("PART_REQUIRED", "Open a local SLDPRT before adding a global variable.");
            path = Program.RequireLocalFixedPath(path, true);
            if (dirty != false) throw new Fault("CLEAN_LOCAL_PART_REQUIRED", "A confirmed clean source is required before adding a global variable.");
            RequireWritableDocument();
            string requestedFeatureName = Catalog.TextValue(args, "feature_name", true, 240);
            string expectedFeatureType = Catalog.TextValue(args, "expected_feature_type", true, 120);
            if (!EditableFeatureType(expectedFeatureType))
                throw new Fault("FEATURE_TYPE_NOT_SUPPORTED", "Only Extrusion, Boss, Cut, HoleWzd, Chamfer and Fillet dimensions are supported in this version.");
            string fullName = Catalog.TextValue(args, "full_name", true, 240);
            double expectedMm = Catalog.Real(args, "expected_current_mm", 0.01, 2000.0);
            double valueMm = Catalog.Real(args, "value_mm", 0.01, 2000.0);
            string variableName = Catalog.TextValue(args, "variable_name", true, 64);
            if (!ValidGlobalVariableName(variableName))
                throw new Fault("INVALID_ARGUMENTS", "variable_name must start with an ASCII letter or underscore and contain only ASCII letters, digits and underscores, 1 to 64 characters.");

            string actualFeatureType;
            object feature = FindExactFeature(requestedFeatureName, out actualFeatureType);
            if (!string.Equals(actualFeatureType, expectedFeatureType, StringComparison.Ordinal))
                throw new Fault("FEATURE_TYPE_STALE", "The current feature type differs from expected_feature_type. Read sw_features again.");
            if (FeatureSuppressed(feature))
                throw new Fault("FEATURE_SUPPRESSED", "A suppressed feature cannot be changed.");

            var request = new ManagedParameterChange { FullName = fullName, ExpectedMm = expectedMm, RequestedMm = valueMm };
            ResolvedManagedParameter resolved = ResolveOwnedFeatureDimension(feature, request);

            object mgr = Call(model, "IModelDoc2", "GetEquationMgr");
            if (mgr == null) throw new Fault("EQUATIONS_MANAGER_UNAVAILABLE", "SOLIDWORKS did not return an equation manager for this document.");
            int existingCount = Convert.ToInt32(Call(mgr, "IEquationMgr", "GetCount"), CultureInfo.InvariantCulture);
            for (int i = 0; i < existingCount; i++)
            {
                string existingLhs = ParseEquationLhs(Text(Get(mgr, "IEquationMgr", "Equation", i)));
                if (existingLhs == null) continue;
                if (string.Equals(existingLhs, variableName, StringComparison.OrdinalIgnoreCase))
                    throw new Fault("GLOBAL_VARIABLE_ALREADY_EXISTS", "A global variable or equation named " + variableName + " already exists in this document.");
                if (string.Equals(existingLhs, resolved.FullName, StringComparison.OrdinalIgnoreCase))
                    throw new Fault("DIMENSION_ALREADY_DRIVEN_BY_EQUATION", "The dimension " + resolved.FullName + " is already driven by an existing equation; remove it manually first.");
            }

            string sourcePath = path;
            string sourceHashBefore = FileSha256(sourcePath);
            string backupPath = CreateLocalBackup(sourcePath, "_BEFORE_GLOBAL_VARIABLE_ADD");
            int bodiesBefore = SolidBodyCount(model);
            double volumeBefore = VolumeOf(model);
            if (bodiesBefore < 1) throw new Fault("FEATURE_GEOMETRY_INVALID", "The source part has no solid body.");
            int newGlobalIndex = -1, newDriveIndex = -1;
            string globalVariableEquation = null, driveEquation = null;
            bool committed = false;
            try
            {
                int equationConfigurationOption = EnumValue("swInConfigurationOpts_e", "swAllConfiguration");
                string localizedDecimalSeparator = CultureInfo.CurrentCulture.NumberFormat.NumberDecimalSeparator;
                string valueText = valueMm.ToString("0.######", CultureInfo.InvariantCulture).Replace(".", localizedDecimalSeparator);
                globalVariableEquation = "\"" + variableName + "\" = " + valueText + "mm";
                RequireWriteTargetUnchanged();
                int appendIndex1 = Convert.ToInt32(Call(mgr, "IEquationMgr", "GetCount"), CultureInfo.InvariantCulture);
                newGlobalIndex = Convert.ToInt32(Call(mgr, "IEquationMgr", "Add3", appendIndex1, globalVariableEquation, true, equationConfigurationOption, null), CultureInfo.InvariantCulture);
                if (newGlobalIndex < 0) throw new Fault("GLOBAL_VARIABLE_ADD_FAILED", "SOLIDWORKS rejected the new global-variable equation " + globalVariableEquation + " (Add3 returned " + newGlobalIndex + " at requested index " + appendIndex1 + ", decimal separator '" + localizedDecimalSeparator + "').");

                RequireWriteTargetUnchanged();
                driveEquation = "\"" + resolved.FullName + "\" = \"" + variableName + "\"";
                int appendIndex2 = Convert.ToInt32(Call(mgr, "IEquationMgr", "GetCount"), CultureInfo.InvariantCulture);
                newDriveIndex = Convert.ToInt32(Call(mgr, "IEquationMgr", "Add3", appendIndex2, driveEquation, true, equationConfigurationOption, null), CultureInfo.InvariantCulture);
                if (newDriveIndex < 0) throw new Fault("DIMENSION_EQUATION_ADD_FAILED", "SOLIDWORKS rejected the equation " + driveEquation + " linking the dimension to the new global variable (Add3 returned " + newDriveIndex + " at requested index " + appendIndex2 + ").");

                RequireWriteTargetUnchanged();
                bool rebuilt = Convert.ToBoolean(Call(model, "IModelDoc2", "EditRebuild3"));
                RequireWriteTargetUnchanged();
                if (!rebuilt) throw new Fault("FEATURE_REBUILD_FAILED", "SOLIDWORKS did not rebuild the part after adding the global variable.");

                string verifiedFeatureType;
                object verifiedFeature = FindExactFeature(requestedFeatureName, out verifiedFeatureType);
                if (!string.Equals(verifiedFeatureType, expectedFeatureType, StringComparison.Ordinal) || FeatureSuppressed(verifiedFeature))
                    throw new Fault("FEATURE_IDENTITY_CHANGED", "The selected feature identity or suppression state changed after rebuild.");

                double actualMm = DimensionSystemValue(resolved.Dimension) * 1000.0;
                double toleranceMm = Math.Max(0.001, Math.Abs(valueMm) * 1e-6);
                if (Math.Abs(actualMm - valueMm) > toleranceMm)
                    throw new Fault("GLOBAL_VARIABLE_VALUE_MISMATCH", "SOLIDWORKS did not preserve the requested value for " + resolved.FullName);

                int countAfter = Convert.ToInt32(Call(mgr, "IEquationMgr", "GetCount"), CultureInfo.InvariantCulture);
                bool globalVerified = false, driveVerified = false;
                for (int i = 0; i < countAfter; i++)
                {
                    string text = Text(Get(mgr, "IEquationMgr", "Equation", i));
                    string lhs = ParseEquationLhs(text);
                    if (lhs == null) continue;
                    if (string.Equals(lhs, variableName, StringComparison.OrdinalIgnoreCase))
                    {
                        object isGlobalRaw = Try("equation.is_global_variable:" + i, delegate { return Get(mgr, "IEquationMgr", "GlobalVariable", i); });
                        if (isGlobalRaw != null && Convert.ToBoolean(isGlobalRaw, CultureInfo.InvariantCulture)) globalVerified = true;
                    }
                    if (string.Equals(lhs, resolved.FullName, StringComparison.OrdinalIgnoreCase) &&
                        text.IndexOf(variableName, StringComparison.OrdinalIgnoreCase) >= 0) driveVerified = true;
                }
                if (!globalVerified) throw new Fault("GLOBAL_VARIABLE_VERIFICATION_FAILED", "The new global variable could not be verified by re-reading IEquationMgr.");
                if (!driveVerified) throw new Fault("GLOBAL_VARIABLE_VERIFICATION_FAILED", "The dimension-linking equation could not be verified by re-reading IEquationMgr.");

                int bodiesAfter = SolidBodyCount(model);
                double volumeAfter = VolumeOf(model);
                if (bodiesAfter != bodiesBefore || bodiesAfter < 1 || volumeAfter <= 0.0)
                    throw new Fault("FEATURE_GEOMETRY_INVALID", "Solid-body count changed or final volume is invalid after adding the global variable.");

                object save = SaveLocalDocumentCore(false);
                string sourceHashAfter = FileSha256(sourcePath);
                if (string.Equals(sourceHashAfter, sourceHashBefore, StringComparison.Ordinal))
                    throw new Fault("FEATURE_FILE_UNCHANGED", "The saved file bytes did not change after adding the global variable.");
                committed = true;
                return Json.Obj("operation", "ADDED_GLOBAL_VARIABLE_AND_LINKED_DIMENSION",
                    "connector_version", Program.Version, "file_path", sourcePath,
                    "backup_path", backupPath, "source_sha256_before", sourceHashBefore,
                    "source_sha256_after", sourceHashAfter, "feature_name", requestedFeatureName,
                    "feature_type", actualFeatureType, "configuration", config,
                    "variable_name", variableName, "dimension_full_name", resolved.FullName,
                    "before_mm", resolved.OriginalM * 1000.0, "value_mm", valueMm, "actual_mm", actualMm,
                    "global_variable_equation", globalVariableEquation, "dimension_equation", driveEquation,
                    "global_variable_equation_index", newGlobalIndex, "dimension_equation_index", newDriveIndex,
                    "verification", Json.Obj("status", "PASS", "rebuilt", true,
                        "feature_identity_confirmed", true, "feature_not_suppressed", true,
                        "global_variable_equation_confirmed", globalVerified,
                        "dimension_equation_confirmed", driveVerified,
                        "solid_body_count_before", bodiesBefore, "solid_body_count_after", bodiesAfter,
                        "volume_before_m3", volumeBefore, "volume_after_m3", volumeAfter,
                        "value_confirmed", true),
                    "save", save, "inside_workspace", Program.IsWorkspacePath(sourcePath),
                    "local_fixed_disk_only", true, "network_paths_allowed", false,
                    "manufacturing_approved", false,
                    "limitations", "Equation text is matched by exact quoted left-hand side only; both equations are added with ConfigurationOption=swAllConfiguration (Add3 rejected swThisConfiguration on this single-configuration document); no formula evaluation or per-configuration classification is performed by the connector.");
            }
            finally
            {
                if (!committed)
                {
                    try
                    {
                        var indices = new List<int>();
                        if (newGlobalIndex >= 0) indices.Add(newGlobalIndex);
                        if (newDriveIndex >= 0) indices.Add(newDriveIndex);
                        indices.Sort();
                        indices.Reverse();
                        foreach (int idx in indices)
                        {
                            try { RequireWriteTargetUnchanged(); Call(mgr, "IEquationMgr", "Delete", idx); }
                            catch { }
                        }
                    }
                    catch { }
                    try
                    {
                        int thisConfigurationFallback = EnumValue("swSetValueInConfiguration_e", "swSetValue_InThisConfiguration");
                        RequireWriteTargetUnchanged();
                        Call(resolved.Dimension, "IDimension", "SetSystemValue3", resolved.OriginalM, thisConfigurationFallback, null);
                        RequireWriteTargetUnchanged();
                        Call(model, "IModelDoc2", "EditRebuild3");
                    }
                    catch { }
                }
            }
        }
        string ManagedParameterFullName(string parameterName)
        {
            if (!ConnectorParameterName(parameterName))
                throw new Fault("PARAMETER_NOT_MANAGED", "Variant parameters must use the AI_ prefix.");
            var matches = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
            var inventory = Json.Map(ParametersData());
            if (Object.Equals(Json.At(inventory, "partial"), true))
                throw new Fault("PARAMETER_INVENTORY_INCOMPLETE", "Cannot verify unique variant parameters from a partial inventory.");
            foreach (object value in (Array)Json.At(inventory, "items"))
            {
                var row = Json.Map(value);
                if (string.Equals(Text(Json.At(row, "name")), parameterName, StringComparison.Ordinal))
                {
                    string fullName = Text(Json.At(row, "full_name"));
                    if (!string.IsNullOrWhiteSpace(fullName)) matches.Add(fullName);
                }
            }
            if (matches.Count != 1)
                throw new Fault("PARAMETER_NAME_NOT_UNIQUE", "Expected exactly one copied parameter named " + parameterName + ", found " + matches.Count + ".");
            foreach (string fullName in matches) return fullName;
            return null;
        }
        object CreateParameterVariant(Dictionary<string, object> args)
        {
            bool workspaceSelector = args.ContainsKey("source_file_name");
            string sourceFileName = workspaceSelector
                ? Catalog.WorkspacePartFileName(args, "source_file_name") : null;
            var requested = ManagedParameterChange.ParseMany(args);
            string sourcePath = workspaceSelector
                ? Path.Combine(Program.EnsureWorkspace(), sourceFileName)
                : Catalog.LocalPartPathText(args, "source_path");
            sourcePath = Program.RequireLocalFixedPath(sourcePath, true);
            OpenLocalPath(sourcePath, requireCleanLoad: true);
            Document();
            if (kind != 1 || !string.Equals(Path.GetFullPath(path), Path.GetFullPath(sourcePath), StringComparison.OrdinalIgnoreCase))
                throw new Fault("SOURCE_PART_NOT_ACTIVE", "Cannot activate the requested local source part.");
            if (dirty != false) throw new Fault("CLEAN_SOURCE_REQUIRED", "A confirmed clean source is required before creating a variant.");

            var sourceParameters = new List<ResolvedManagedParameter>();
            foreach (ManagedParameterChange item in requested) sourceParameters.Add(ResolveManagedParameter(item));
            object sourceModel = model;
            string sourceTitle = title;
            string sourceHashBefore = FileSha256(sourcePath);
            string destination = UniqueLocalOutputPath(sourcePath, "_VARIANT", ".SLDPRT");
            string variantTitle = null;
            bool copied = false;
            try
            {
                File.Copy(sourcePath, destination, false);
                copied = true;
                if (!File.Exists(destination) || !string.Equals(FileSha256(destination), sourceHashBefore, StringComparison.Ordinal))
                    throw new Fault("VARIANT_COPY_FAILED", "Cannot verify the new parameter-variant copy.");
                OpenLocalPath(destination, requireCleanLoad: true);
                Document();
                variantTitle = title;

                var variantRequests = new List<ManagedParameterChange>();
                for (int i = 0; i < sourceParameters.Count; i++)
                {
                    ResolvedManagedParameter sourceParameter = sourceParameters[i];
                    variantRequests.Add(new ManagedParameterChange {
                        FullName = ManagedParameterFullName(sourceParameter.Name),
                        ExpectedMm = sourceParameter.Request.ExpectedMm,
                        RequestedMm = sourceParameter.Request.RequestedMm
                    });
                }
                var result = Json.Map(SetWorkspaceParametersCore(variantRequests, false, false));
                string sourceHashAfter = FileSha256(sourcePath);
                bool sourceUnchanged = string.Equals(Text(Call(sourceModel, "IModelDoc2", "GetTitle")), sourceTitle, StringComparison.Ordinal) &&
                    string.Equals(Text(Call(sourceModel, "IModelDoc2", "GetPathName")), sourcePath, StringComparison.OrdinalIgnoreCase) &&
                    !Convert.ToBoolean(Call(sourceModel, "IModelDoc2", "GetSaveFlag")) &&
                    string.Equals(sourceHashAfter, sourceHashBefore, StringComparison.Ordinal);
                if (!sourceUnchanged) throw new Fault("SOURCE_CHANGED", "The source part changed while the variant was created.");
                result["operation"] = "CREATED_LOCAL_PARAMETER_VARIANT";
                result.Add("source_file_name", Path.GetFileName(sourcePath));
                result.Add("source_path", sourcePath);
                result.Add("source_unchanged", true);
                result.Add("source_sha256_before", sourceHashBefore);
                result.Add("source_sha256_after", sourceHashAfter);
                result.Add("variant_path", destination);
                result.Add("variant_active", true);
                result.Add("rollback_source_path", sourcePath);
                result.Add("source_inside_workspace", Program.IsWorkspacePath(sourcePath));
                result["inside_workspace"] = Program.IsWorkspacePath(destination);
                return result;
            }
            catch
            {
                if (copied)
                {
                    try { if (!string.IsNullOrEmpty(variantTitle)) Call(app, "ISldWorks", "CloseDoc", variantTitle); } catch { }
                    try { if (File.Exists(destination)) File.Delete(destination); } catch { }
                }
                throw;
            }
        }
        object CreateDrawing(Dictionary<string, object> args)
        {
            Document();
            if (kind != 1) throw new Fault("PART_REQUIRED", "Open a local SLDPRT before creating a drawing.");
            path = Program.RequireLocalFixedPath(path, true);
            if (dirty != false) throw new Fault("CLEAN_LOCAL_PART_REQUIRED", "A confirmed clean part is required before creating its drawing.");
            string sourcePath = path, sourceTitle = title;
            string sourceHashBefore = FileSha256(sourcePath);
            string projection = Catalog.TextValue(args, "projection", false, 20) ?? "first_angle";
            string dimensionMode = Catalog.TextValue(args, "dimensions", false, 20) ?? "model";
            string templateSource;
            string template = FindDrawingTemplate(out templateSource);
            object created = null; string createdTitle = null; bool saved = false;
            try
            {
                created = Call(app, "ISldWorks", "NewDocument", template, 0, 0.0, 0.0);
                if (created == null || Convert.ToInt32(Call(created, "IModelDoc2", "GetType")) != 3)
                    throw new Fault("CREATE_DRAWING_FAILED", "The selected .drwdot template did not create a drawing document.");
                createdTitle = Text(Call(created, "IModelDoc2", "GetTitle"));
                string apiMethod = projection == "third_angle" ? "Create3rdAngleViews2" : "Create1stAngleViews2";
                bool viewsCreated = Convert.ToBoolean(Call(created, "IDrawingDoc", apiMethod, sourcePath));
                if (!viewsCreated) throw new Fault("DRAWING_VIEWS_FAILED", "SOLIDWORKS did not create standard views from the local part.");
                int referencedViews = 0, guard = 0;
                object view = Call(created, "IDrawingDoc", "GetFirstView");
                while (view != null && guard++ < 100)
                {
                    string referenced = Text(Call(view, "IView", "GetReferencedModelName"));
                    if (!string.IsNullOrWhiteSpace(referenced)) referencedViews++;
                    view = Call(view, "IView", "GetNextView");
                }
                if (referencedViews < 1) throw new Fault("DRAWING_VERIFICATION_FAILED", "No model view referencing the local part was found in the new drawing.");
                bool modelDimensionsRequested = dimensionMode == "model";
                int importedDimensionCount = 0;
                int insertedAnnotationCount = 0;
                int totalDisplayDimensionCount = CountDrawingDimensions(created);
                if (modelDimensionsRequested)
                {
                    int importEntireModel = EnumValue("swImportModelItemsSource_e",
                        "swImportModelItemsFromEntireModel");
                    int markedDimensions = EnumValue("swInsertAnnotation_e",
                        "swInsertDimensionsMarkedForDrawing");
                    int beforeImportCount = totalDisplayDimensionCount;
                    // Import dimensions explicitly marked for drawing from the entire
                    // model. DuplicateDims=true asks SOLIDWORKS to eliminate duplicate
                    // dimensions across the standard views.
                    object inserted = Call(created, "IDrawingDoc", "InsertModelAnnotations3",
                        importEntireModel, markedDimensions, true, true, false, false);
                    var insertedArray = inserted as Array;
                    insertedAnnotationCount = insertedArray == null ? 0 : insertedArray.Length;
                    totalDisplayDimensionCount = CountDrawingDimensions(created);
                    importedDimensionCount = totalDisplayDimensionCount - beforeImportCount;
                    if (totalDisplayDimensionCount < 1)
                        throw new Fault("NO_MODEL_DIMENSIONS_IMPORTED", "The SLDPRT has no model dimensions marked for drawing. Use dimensions=none for a views-only draft, or create the part with real driving dimensions first.");
                }
                string outputPath = UniqueLocalOutputPath(sourcePath, "_DRAWING", ".SLDDRW");
                var extension = Get(created, "IModelDoc2", "Extension");
                object[] saveArgs = { outputPath, 0, 1, null, null, 0, 0 };
                bool saveOk = Convert.ToBoolean(Call(extension, "IModelDocExtension", "SaveAs3", saveArgs));
                int saveErrors = Convert.ToInt32(saveArgs[5], CultureInfo.InvariantCulture);
                int saveWarnings = Convert.ToInt32(saveArgs[6], CultureInfo.InvariantCulture);
                string confirmedPath = Text(Call(created, "IModelDoc2", "GetPathName"));
                bool pathConfirmed = string.Equals(confirmedPath, outputPath, StringComparison.OrdinalIgnoreCase) &&
                    File.Exists(outputPath) && Program.IsLocalFixedPath(outputPath, true);
                if (!saveOk || saveErrors != 0 || !pathConfirmed)
                    throw new Fault("SAVE_FAILED", "SOLIDWORKS did not save the drawing. success=" + saveOk + ", errors=" + saveErrors + ", warnings=" + saveWarnings);
                saved = true;
                string sourceHashAfter = FileSha256(sourcePath);
                bool sourceUnchanged = string.Equals(Text(Call(model, "IModelDoc2", "GetTitle")), sourceTitle, StringComparison.Ordinal) &&
                    string.Equals(Text(Call(model, "IModelDoc2", "GetPathName")), sourcePath, StringComparison.OrdinalIgnoreCase) &&
                    Bool(Call(model, "IModelDoc2", "GetSaveFlag")) == false &&
                    string.Equals(sourceHashAfter, sourceHashBefore, StringComparison.Ordinal);
                if (!sourceUnchanged) throw new Fault("SOURCE_CHANGED", "The local source part changed while its drawing was generated.");
                return Json.Obj("operation", "CREATED_LOCAL_DRAWING", "connector_version", Program.Version,
                    "file_path", outputPath, "source_part_path", sourcePath, "source_part_unchanged", true,
                    "source_sha256_before", sourceHashBefore, "source_sha256_after", sourceHashAfter,
                    "projection", projection, "dimensions", Json.Obj("mode", dimensionMode,
                        "source", modelDimensionsRequested ? "MARKED_FOR_DRAWING_MODEL_DIMENSIONS" : "NONE",
                        "api_inserted_annotation_count", insertedAnnotationCount,
                        "display_dimension_count_before_explicit_import", totalDisplayDimensionCount - importedDimensionCount,
                        "display_dimension_count_added_by_explicit_import", importedDimensionCount,
                        "verified_display_dimension_count", totalDisplayDimensionCount,
                        "inferred_dimensions", 0, "tolerances_added", 0),
                    "template", Json.Obj("path", template, "source", templateSource),
                    "verification", Json.Obj("status", "PASS", "referenced_model_view_count", referencedViews,
                        "display_dimension_count", totalDisplayDimensionCount,
                        "display_dimension_count_added_by_explicit_import", importedDimensionCount,
                        "method", "IDrawingDoc." + apiMethod + " + IView.GetReferencedModelName + IView.GetFirstDisplayDimension5/IDisplayDimension.GetNext5"),
                    "save", Json.Obj("method", "IModelDocExtension.SaveAs3", "api_success", saveOk,
                        "errors", saveErrors, "warnings", saveWarnings, "path_confirmed", pathConfirmed),
                    "drawing_scope", "Standard views plus model dimensions explicitly marked for drawing when dimensions=model. No inferred dimensions, tolerances, surface finish, welding symbols, title-block approval or independent drawing validation were added.",
                    "inside_workspace", Program.IsWorkspacePath(outputPath), "local_fixed_disk_only", true,
                    "network_paths_allowed", false, "manufacturing_approved", false);
            }
            catch
            {
                if (!saved && created != null && !string.IsNullOrEmpty(createdTitle))
                    try { Call(app, "ISldWorks", "CloseDoc", createdTitle); } catch { }
                throw;
            }
        }
        int CountDrawingDimensions(object drawing)
        {
            int count = 0, viewGuard = 0;
            object view = Call(drawing, "IDrawingDoc", "GetFirstView");
            while (view != null && viewGuard++ < 100)
            {
                int dimensionGuard = 0;
                object displayDimension = Call(view, "IView", "GetFirstDisplayDimension5");
                while (displayDimension != null && dimensionGuard++ < 2000)
                {
                    count++;
                    displayDimension = Call(displayDimension, "IDisplayDimension", "GetNext5");
                }
                if (dimensionGuard >= 2000)
                    throw new Fault("DRAWING_VERIFICATION_FAILED", "Display-dimension traversal exceeded the safety limit.");
                view = Call(view, "IView", "GetNextView");
            }
            if (viewGuard >= 100)
                throw new Fault("DRAWING_VERIFICATION_FAILED", "Drawing-view traversal exceeded the safety limit.");
            return count;
        }
        int CountViewDimensions(object view)
        {
            int count = 0, guard = 0;
            object displayDimension = Call(view, "IView", "GetFirstDisplayDimension5");
            while (displayDimension != null && guard++ < 2000)
            {
                count++;
                displayDimension = Call(displayDimension, "IDisplayDimension", "GetNext5");
            }
            if (guard >= 2000)
                throw new Fault("DRAWING_VERIFICATION_FAILED", "Display-dimension traversal exceeded the safety limit.");
            return count;
        }
        object DrawingData()
        {
            if (kind != 3) throw new Fault("DRAWING_REQUIRED", "sw_drawing requires an active SLDDRW drawing.");
            var sheetNamesRaw = Call(model, "IDrawingDoc", "GetSheetNames") as Array;
            var sheetNames = new List<object>();
            if (sheetNamesRaw != null)
                foreach (object item in sheetNamesRaw) sheetNames.Add(Text(item));
            var views = new List<object>();
            var referencedModels = new List<string>();
            int allViews = 0, modelViews = 0, guard = 0;
            object view = Call(model, "IDrawingDoc", "GetFirstView");
            while (view != null && guard++ < 100)
            {
                allViews++;
                string referenced = Text(Call(view, "IView", "GetReferencedModelName"));
                if (!string.IsNullOrWhiteSpace(referenced))
                {
                    modelViews++;
                    bool known = false;
                    foreach (string existing in referencedModels)
                        if (string.Equals(existing, referenced, StringComparison.OrdinalIgnoreCase)) { known = true; break; }
                    if (!known) referencedModels.Add(referenced);
                    views.Add(Json.Obj("referenced_model", referenced,
                        "display_dimension_count", CountViewDimensions(view)));
                }
                view = Call(view, "IView", "GetNextView");
            }
            if (guard >= 100)
                throw new Fault("DRAWING_VERIFICATION_FAILED", "Drawing-view traversal exceeded the safety limit.");
            int dimensions = CountDrawingDimensions(model);
            return Json.Obj("sheet_names", sheetNames.ToArray(), "sheet_count", sheetNames.Count,
                "all_view_count_including_sheet_views", allViews, "referenced_model_view_count", modelViews,
                "referenced_models", referencedModels.ToArray(), "views", views.ToArray(),
                "display_dimension_count", dimensions, "view_scope", "ACTIVE_SHEET_ONLY",
                "verification", Json.Obj("status", modelViews > 0 ? "PASS" : "INCOMPLETE",
                    "method", "IDrawingDoc.GetSheetNames + IDrawingDoc.GetFirstView + IView.GetNextView + IView.GetReferencedModelName + IView.GetFirstDisplayDimension5"),
                "scope", "API inventory only. Dimension values, tolerances, notes, overlaps, title-block completion and manufacturing correctness are not approved.");
        }
        internal static bool IsPdfHeader(byte[] bytes)
        {
            return bytes != null && bytes.Length >= 5 && bytes[0] == 0x25 && bytes[1] == 0x50 &&
                bytes[2] == 0x44 && bytes[3] == 0x46 && bytes[4] == 0x2D;
        }
        static bool HasPdfHeader(string filePath)
        {
            byte[] bytes = new byte[5];
            using (var stream = new FileStream(filePath, FileMode.Open, FileAccess.Read, FileShare.Read))
                if (stream.Read(bytes, 0, bytes.Length) != bytes.Length) return false;
            return IsPdfHeader(bytes);
        }
        object ExportWorkspacePdf()
        {
            Document();
            if (kind != 3) throw new Fault("DRAWING_REQUIRED", "Open a saved local SLDDRW before exporting PDF.");
            path = Program.RequireLocalFixedPath(path, true);
            if (dirty != false) throw new Fault("CLEAN_LOCAL_DRAWING_REQUIRED", "A confirmed clean drawing is required before exporting PDF.");
            string sourcePath = path, sourceTitle = title;
            string sourceHashBefore = FileSha256(sourcePath);
            string outputPath = UniqueLocalOutputPath(sourcePath, "_PDF", ".PDF");
            bool success = false;
            try
            {
                var extension = Get(model, "IModelDoc2", "Extension");
                object[] saveArgs = { outputPath, 0, 1, null, null, 0, 0 };
                bool saveOk = Convert.ToBoolean(Call(extension, "IModelDocExtension", "SaveAs3", saveArgs));
                int errors = Convert.ToInt32(saveArgs[5], CultureInfo.InvariantCulture);
                int warnings = Convert.ToInt32(saveArgs[6], CultureInfo.InvariantCulture);
                bool exists = File.Exists(outputPath);
                long size = exists ? new FileInfo(outputPath).Length : 0;
                bool pdfHeader = exists && HasPdfHeader(outputPath);
                string sourceHashAfter = FileSha256(sourcePath);
                bool sourceUnchanged = Text(Call(model, "IModelDoc2", "GetTitle")) == sourceTitle &&
                    Text(Call(model, "IModelDoc2", "GetPathName")) == sourcePath &&
                    Bool(Call(model, "IModelDoc2", "GetSaveFlag")) == false &&
                    string.Equals(sourceHashAfter, sourceHashBefore, StringComparison.Ordinal);
                if (!saveOk || errors != 0 || !exists || size < 5 || !pdfHeader ||
                    !Program.IsLocalFixedPath(outputPath, true) || !sourceUnchanged)
                    throw new Fault("PDF_EXPORT_FAILED", "PDF export verification failed. success=" + saveOk +
                        ", errors=" + errors + ", exists=" + exists + ", size=" + size +
                        ", pdf_header=" + pdfHeader + ", source_unchanged=" + sourceUnchanged);
                success = true;
                return Json.Obj("operation", "EXPORTED_LOCAL_DRAWING_PDF", "connector_version", Program.Version,
                    "file_path", outputPath, "source_drawing_path", sourcePath, "source_drawing_unchanged", true,
                    "source_sha256_before", sourceHashBefore, "source_sha256_after", sourceHashAfter,
                    "size_bytes", size, "verification", Json.Obj("status", "PASS", "pdf_header", "%PDF-",
                        "path_on_local_fixed_disk", true, "source_drawing_unchanged", true),
                    "save", Json.Obj("method", "IModelDocExtension.SaveAs3", "api_success", saveOk,
                        "errors", errors, "warnings", warnings),
                    "inside_workspace", Program.IsWorkspacePath(outputPath), "local_fixed_disk_only", true,
                    "network_paths_allowed", false,
                    "manufacturing_approved", false);
            }
            finally
            {
                if (!success && File.Exists(outputPath))
                    try { File.Delete(outputPath); } catch { }
            }
        }
        double VolumeOf(object target)
        {
            Call(target, "IModelDoc2", "ClearSelection2", true);
            var ext = Get(target, "IModelDoc2", "Extension");
            var mass = Call(ext, "IModelDocExtension", "CreateMassProperty");
            if (mass == null) throw new Fault("GEOMETRY_VERIFICATION_FAILED", "Cannot calculate volume of the generated part.");
            var units = Face("IMassProperty").GetProperty("UseSystemUnits");
            units.SetValue(mass, true, null);
            double volume = Convert.ToDouble(Get(mass, "IMassProperty", "Volume"), CultureInfo.InvariantCulture);
            if (double.IsNaN(volume) || double.IsInfinity(volume) || volume <= 0)
                throw new Fault("GEOMETRY_VERIFICATION_FAILED", "Generated part has invalid volume.");
            return volume;
        }
        internal static bool CylinderRadiiMatch(IList<double> actualRadiiMm, double? outerRadiusMm,
            IList<double> holeRadiiMm)
        {
            var expectedRadiiMm = new List<double>();
            if (outerRadiusMm.HasValue) expectedRadiiMm.Add(outerRadiusMm.Value);
            foreach (double radius in holeRadiiMm) expectedRadiiMm.Add(radius);
            if (actualRadiiMm.Count != expectedRadiiMm.Count) return false;
            var used = new bool[actualRadiiMm.Count];
            foreach (double expected in expectedRadiiMm)
            {
                int match = -1;
                double toleranceMm = Math.Max(0.001, Math.Abs(expected) * 1e-6);
                for (int i = 0; i < actualRadiiMm.Count; i++)
                    if (!used[i] && Math.Abs(actualRadiiMm[i] - expected) <= toleranceMm) { match = i; break; }
                if (match < 0) return false;
                used[match] = true;
            }
            return true;
        }
        object VerifyPrismaticCylinders(object target, double? outerRadiusMm, IList<double> holeRadiiMm,
            IList<double> additionalCutRadiiMm = null, IList<double> bossRadiiMm = null,
            IList<double> outerProfileRadiiMm = null)
        {
            int solidBody = EnumValue("swBodyType_e", "swSolidBody");
            var bodies = Call(target, "IPartDoc", "GetBodies2", solidBody, false) as Array;
            if (bodies == null || bodies.Length != 1)
                throw new Fault("GEOMETRY_TOPOLOGY_MISMATCH",
                    "The generated prismatic part must contain exactly one solid body. The file was not saved.");

            var actualRadiiMm = new List<double>();
            foreach (object body in bodies)
            {
                var faces = Call(body, "IBody2", "GetFaces") as Array;
                if (faces == null) continue;
                foreach (object face in faces)
                {
                    object surface = Call(face, "IFace2", "GetSurface");
                    if (surface == null || !Convert.ToBoolean(Call(surface, "ISurface", "IsCylinder"))) continue;
                    var parameters = Get(surface, "ISurface", "CylinderParams") as Array;
                    if (parameters == null || parameters.Length < 7)
                        throw new Fault("GEOMETRY_TOPOLOGY_MISMATCH",
                            "SOLIDWORKS returned a cylindrical face without readable cylinder parameters. The file was not saved.");
                    double radiusMm = Convert.ToDouble(parameters.GetValue(6), CultureInfo.InvariantCulture) * 1000.0;
                    if (double.IsNaN(radiusMm) || double.IsInfinity(radiusMm) || radiusMm <= 0.0)
                        throw new Fault("GEOMETRY_TOPOLOGY_MISMATCH",
                            "SOLIDWORKS returned an invalid cylindrical radius. The file was not saved.");
                    actualRadiiMm.Add(radiusMm);
                }
            }

            var allCutRadiiMm = new List<double>();
            foreach (double radius in holeRadiiMm) allCutRadiiMm.Add(radius);
            if (additionalCutRadiiMm != null)
                foreach (double radius in additionalCutRadiiMm) allCutRadiiMm.Add(radius);
            var allAdditionalRadiiMm = new List<double>();
            foreach (double radius in allCutRadiiMm) allAdditionalRadiiMm.Add(radius);
            if (bossRadiiMm != null)
                foreach (double radius in bossRadiiMm) allAdditionalRadiiMm.Add(radius);
            if (outerProfileRadiiMm != null)
                foreach (double radius in outerProfileRadiiMm) allAdditionalRadiiMm.Add(radius);
            int expectedCylinderCount = allAdditionalRadiiMm.Count + (outerRadiusMm.HasValue ? 1 : 0);
            if (!CylinderRadiiMatch(actualRadiiMm, outerRadiusMm, allAdditionalRadiiMm))
                throw new Fault("GEOMETRY_TOPOLOGY_MISMATCH",
                    "The generated B-rep cylindrical faces do not match the validated outer circle, holes, cuts and bosses. " +
                    "Expected " + expectedCylinderCount + ", found " + actualRadiiMm.Count + ". The file was not saved.");

            actualRadiiMm.Sort();
            var actualDiametersMm = new List<double>();
            foreach (double radius in actualRadiiMm) actualDiametersMm.Add(radius * 2.0);
            return Json.Obj("status", "PASS",
                "method", "IPartDoc.GetBodies2 + IBody2.GetFaces + IFace2.GetSurface + ISurface.IsCylinder/CylinderParams",
                "solid_body_count", bodies.Length,
                "expected_cylindrical_face_count", expectedCylinderCount,
                "actual_cylindrical_face_count", actualRadiiMm.Count,
                "actual_diameters_mm", actualDiametersMm.ToArray(),
                "outer_circle", outerRadiusMm.HasValue ? (object)Json.Obj(
                    "status", "PASS", "expected_diameter_mm", outerRadiusMm.Value * 2.0,
                    "analytic_cylindrical_surface_confirmed", true) : null,
                "through_holes", Json.Obj("status", "PASS", "expected_count", holeRadiiMm.Count,
                    "analytic_cylindrical_surface_count", holeRadiiMm.Count),
                "additional_cylindrical_cuts", Json.Obj("status", "PASS",
                    "expected_count", additionalCutRadiiMm == null ? 0 : additionalCutRadiiMm.Count,
                    "analytic_cylindrical_surface_count", additionalCutRadiiMm == null ? 0 : additionalCutRadiiMm.Count),
                "circular_bosses", Json.Obj("status", "PASS",
                    "expected_count", bossRadiiMm == null ? 0 : bossRadiiMm.Count,
                    "analytic_cylindrical_surface_count", bossRadiiMm == null ? 0 : bossRadiiMm.Count),
                "rounded_outer_profile_corners", Json.Obj("status", "PASS",
                    "expected_count", outerProfileRadiiMm == null ? 0 : outerProfileRadiiMm.Count,
                    "analytic_cylindrical_surface_count", outerProfileRadiiMm == null ? 0 : outerProfileRadiiMm.Count),
                "tolerance", "max(0.001 mm, radius*1e-6)");
        }

        object BeginBossSketch(object target)
        {
            object plane = FirstReferencePlane(target);
            if (!Convert.ToBoolean(Call(plane, "IFeature", "Select2", false, 0)))
                throw new Fault("SKETCH_PLANE_NOT_FOUND", "Cannot select the base reference plane for a validated boss.");
            object sketch = Get(target, "IModelDoc2", "SketchManager");
            Call(sketch, "ISketchManager", "InsertSketch", true);
            return sketch;
        }

        object FinishBossSketch(object target, object sketch, double extrusionMm, string label)
        {
            Call(sketch, "ISketchManager", "InsertSketch", true);
            object features = Get(target, "IModelDoc2", "FeatureManager");
            int blind = EnumValue("swEndConditions_e", "swEndCondBlind");
            int sketchPlane = EnumValue("swStartConditions_e", "swStartSketchPlane");
            // The base extrusion uses Dir=false. Dir=true deliberately grows the boss
            // from the exposed reference-plane side, away from the base body.
            object boss = Call(features, "IFeatureManager", "FeatureExtrusion2",
                true, false, true, blind, blind, extrusionMm / 1000.0, extrusionMm / 1000.0,
                false, false, false, false, 0.0, 0.0, false, false, false, false,
                true, true, true, sketchPlane, 0.0, false);
            if (boss == null) throw new Fault("BOSS_FAILED", "SOLIDWORKS did not create " + label + ".");
            Call(target, "IModelDoc2", "EditRebuild3");
            return boss;
        }

        void CreateRectangularBoss(object target, RectangularBoss boss)
        {
            if (boss.CornerStyle == null)
            {
                CreateRectangleBossPrimitive(target, boss.X, boss.Y, boss.Width, boss.Height,
                    boss.Extrusion, "a sharp rectangular boss");
            }
            else if (boss.CornerStyle == "chamfer")
            {
                double left = boss.X - boss.Width / 2.0, right = boss.X + boss.Width / 2.0;
                double bottom = boss.Y - boss.Height / 2.0, top = boss.Y + boss.Height / 2.0;
                double size = boss.CornerSize;
                double overlap = Math.Min(0.01, size / 10.0);
                CreateRectangleBossPrimitive(target, boss.X, boss.Y, boss.Width, boss.Height - 2.0 * size,
                    boss.Extrusion, "the horizontal core of a chamfered rectangular boss");
                CreateRectangleBossPrimitive(target, boss.X, boss.Y, boss.Width - 2.0 * size, boss.Height,
                    boss.Extrusion, "the vertical core of a chamfered rectangular boss");
                CreatePolygonBossPrimitive(target, new List<double[]> {
                    new[] { left + size, top }, new[] { left, top - size },
                    new[] { left + size + overlap, top - size - overlap }
                }, boss.Extrusion, "the top-left chamfer corner");
                CreatePolygonBossPrimitive(target, new List<double[]> {
                    new[] { right - size, top }, new[] { right, top - size },
                    new[] { right - size - overlap, top - size - overlap }
                }, boss.Extrusion, "the top-right chamfer corner");
                CreatePolygonBossPrimitive(target, new List<double[]> {
                    new[] { right, bottom + size }, new[] { right - size, bottom },
                    new[] { right - size - overlap, bottom + size + overlap }
                }, boss.Extrusion, "the bottom-right chamfer corner");
                CreatePolygonBossPrimitive(target, new List<double[]> {
                    new[] { left + size, bottom }, new[] { left, bottom + size },
                    new[] { left + size + overlap, bottom + size + overlap }
                }, boss.Extrusion, "the bottom-left chamfer corner");
            }
            else
            {
                double left = boss.X - boss.Width / 2.0, right = boss.X + boss.Width / 2.0;
                double bottom = boss.Y - boss.Height / 2.0, top = boss.Y + boss.Height / 2.0;
                double radius = boss.CornerSize;
                CreateRectangleBossPrimitive(target, boss.X, boss.Y, boss.Width, boss.Height - 2.0 * radius,
                    boss.Extrusion, "the horizontal core of a rounded rectangular boss");
                CreateRectangleBossPrimitive(target, boss.X, boss.Y, boss.Width - 2.0 * radius, boss.Height,
                    boss.Extrusion, "the vertical core of a rounded rectangular boss");
                CreateCircleBossPrimitive(target, left + radius, top - radius, radius, boss.Extrusion,
                    "the top-left round corner");
                CreateCircleBossPrimitive(target, right - radius, top - radius, radius, boss.Extrusion,
                    "the top-right round corner");
                CreateCircleBossPrimitive(target, right - radius, bottom + radius, radius, boss.Extrusion,
                    "the bottom-right round corner");
                CreateCircleBossPrimitive(target, left + radius, bottom + radius, radius, boss.Extrusion,
                    "the bottom-left round corner");
            }
        }

        void CreateRectangleBossPrimitive(object target, double xMm, double yMm,
            double widthMm, double heightMm, double extrusionMm, string label)
        {
            object sketch = BeginBossSketch(target);
            object segments = Call(sketch, "ISketchManager", "CreateCenterRectangle",
                xMm / 1000.0, yMm / 1000.0, 0.0,
                (xMm + widthMm / 2.0) / 1000.0, (yMm + heightMm / 2.0) / 1000.0, 0.0);
            if (segments == null) throw new Fault("SKETCH_FAILED", "Cannot sketch " + label + ".");
            FinishBossSketch(target, sketch, extrusionMm, label);
        }

        void CreatePolygonBossPrimitive(object target, List<double[]> points,
            double extrusionMm, string label)
        {
            object sketch = BeginBossSketch(target);
            SketchClosedPolygon(sketch, points, label);
            FinishBossSketch(target, sketch, extrusionMm, label);
        }

        void CreateCircleBossPrimitive(object target, double xMm, double yMm,
            double radiusMm, double extrusionMm, string label)
        {
            object sketch = BeginBossSketch(target);
            if (Call(sketch, "ISketchManager", "CreateCircleByRadius", xMm / 1000.0,
                yMm / 1000.0, 0.0, radiusMm / 1000.0) == null)
                throw new Fault("SKETCH_FAILED", "Cannot sketch " + label + ".");
            FinishBossSketch(target, sketch, extrusionMm, label);
        }

        void CreateCircularBoss(object target, CircularBoss boss)
        {
            object sketch = BeginBossSketch(target);
            if (Call(sketch, "ISketchManager", "CreateCircleByRadius", boss.X / 1000.0,
                boss.Y / 1000.0, 0.0, boss.Radius / 1000.0) == null)
                throw new Fault("SKETCH_FAILED", "Cannot sketch a validated circular boss.");
            FinishBossSketch(target, sketch, boss.Extrusion, "a validated circular boss");
        }

        object VerifyAddedVolume(double beforeM3, double afterM3, double expectedAddedM3,
            string type, object parameters)
        {
            double actualAddedM3 = afterM3 - beforeM3;
            double relativeError = Math.Abs(actualAddedM3 - expectedAddedM3) / expectedAddedM3;
            if (actualAddedM3 <= 0.0 || relativeError > 0.001)
                throw new Fault("BOSS_VERIFICATION_FAILED", "The " + type +
                    " added a volume that differs from the validated plan by more than 0.1%. The file was not saved.");
            return Json.Obj("type", type, "status", "PASS", "parameters", parameters,
                "expected_added_volume_m3", expectedAddedM3,
                "actual_added_volume_m3", actualAddedM3, "relative_error", relativeError);
        }

        object BeginCutSketch(object target)
        {
            object plane = FirstReferencePlane(target);
            if (!Convert.ToBoolean(Call(plane, "IFeature", "Select2", false, 0)))
                throw new Fault("SKETCH_PLANE_NOT_FOUND", "Cannot select the base reference plane for a validated pocket or slot.");
            object sketch = Get(target, "IModelDoc2", "SketchManager");
            Call(sketch, "ISketchManager", "InsertSketch", true);
            return sketch;
        }

        object FinishCutSketch(object target, object sketch, bool through, double depthMm, string label,
            bool allowDirectionFallback = false)
        {
            Call(sketch, "ISketchManager", "InsertSketch", true);
            object features = Get(target, "IModelDoc2", "FeatureManager");
            int blind = EnumValue("swEndConditions_e", "swEndCondBlind");
            int firstEnd = through ? EnumValue("swEndConditions_e", "swEndCondThroughAll") : blind;
            int sketchPlane = EnumValue("swStartConditions_e", "swStartSketchPlane");
            object cut = Call(features, "IFeatureManager", "FeatureCut4",
                true, false, true, firstEnd, blind, depthMm / 1000.0, depthMm / 1000.0,
                false, false, false, false, 0.0, 0.0, false, false, false, false,
                false, true, true, false, false, false, sketchPlane, 0.0, false, false);
            if (cut == null && allowDirectionFallback)
            {
                // A Blind cut's removal direction follows the sketch plane's own
                // normal, which can point away from the material rather than into
                // it depending on which side of a reference plane the solid sits
                // on (unlike ThroughAll, which finds material regardless of
                // direction). Rather than guess the correct sign for every
                // reference-plane orientation in advance, retry once with the
                // opposite direction before giving up. Only opted into by callers
                // that know their sketch plane may be coincident with a solid
                // face on either side; existing callers are unaffected.
                cut = Call(features, "IFeatureManager", "FeatureCut4",
                    true, false, false, firstEnd, blind, depthMm / 1000.0, depthMm / 1000.0,
                    false, false, false, false, 0.0, 0.0, false, false, false, false,
                    false, true, true, false, false, false, sketchPlane, 0.0, false, false);
            }
            if (cut == null) throw new Fault("CUT_FAILED", "SOLIDWORKS did not create " + label + ".");
            Call(target, "IModelDoc2", "EditRebuild3");
            return cut;
        }

        void CreateRectangularPocketCut(object target, RectangularPocket pocket)
        {
            object sketch = BeginCutSketch(target);
            object segments = Call(sketch, "ISketchManager", "CreateCenterRectangle",
                pocket.X / 1000.0, pocket.Y / 1000.0, 0.0,
                (pocket.X + pocket.Width / 2.0) / 1000.0,
                (pocket.Y + pocket.Height / 2.0) / 1000.0, 0.0);
            if (segments == null) throw new Fault("SKETCH_FAILED", "Cannot sketch a validated rectangular pocket.");
            FinishCutSketch(target, sketch, false, pocket.Depth, "a validated rectangular blind pocket");
        }

        void CreateCircularPocketCut(object target, CircularPocket pocket)
        {
            object sketch = BeginCutSketch(target);
            if (Call(sketch, "ISketchManager", "CreateCircleByRadius", pocket.X / 1000.0,
                pocket.Y / 1000.0, 0.0, pocket.Radius / 1000.0) == null)
                throw new Fault("SKETCH_FAILED", "Cannot sketch a validated circular pocket.");
            FinishCutSketch(target, sketch, false, pocket.Depth, "a validated circular blind pocket");
        }

        void CreateStraightSlotCut(object target, StraightSlot slot)
        {
            double dx = slot.X2 - slot.X1, dy = slot.Y2 - slot.Y1;
            double length = slot.LengthMm;
            double nx = -dy / length * slot.Radius, ny = dx / length * slot.Radius;
            object rectangleSketch = BeginCutSketch(target);
            var rectangle = new List<double[]> {
                new[] { slot.X1 + nx, slot.Y1 + ny }, new[] { slot.X2 + nx, slot.Y2 + ny },
                new[] { slot.X2 - nx, slot.Y2 - ny }, new[] { slot.X1 - nx, slot.Y1 - ny }
            };
            SketchClosedPolygon(rectangleSketch, rectangle, "the straight-slot centre rectangle");
            FinishCutSketch(target, rectangleSketch, slot.Through, slot.Depth, "the straight-slot centre rectangle");

            object capSketch = BeginCutSketch(target);
            if (Call(capSketch, "ISketchManager", "CreateCircleByRadius", slot.X1 / 1000.0,
                slot.Y1 / 1000.0, 0.0, slot.Radius / 1000.0) == null ||
                Call(capSketch, "ISketchManager", "CreateCircleByRadius", slot.X2 / 1000.0,
                slot.Y2 / 1000.0, 0.0, slot.Radius / 1000.0) == null)
                throw new Fault("SKETCH_FAILED", "Cannot sketch both validated straight-slot end caps.");
            FinishCutSketch(target, capSketch, slot.Through, slot.Depth, "the straight-slot circular end caps");
        }

        object VerifyCutVolume(double beforeM3, double afterM3, double expectedRemovedM3,
            string type, object parameters)
        {
            double actualRemovedM3 = beforeM3 - afterM3;
            double relativeError = Math.Abs(actualRemovedM3 - expectedRemovedM3) / expectedRemovedM3;
            if (actualRemovedM3 <= 0.0 || relativeError > 0.001)
                throw new Fault("CUT_VERIFICATION_FAILED", "The " + type +
                    " removed a volume that differs from the validated plan by more than 0.1%. The file was not saved.");
            return Json.Obj("type", type, "status", "PASS", "parameters", parameters,
                "expected_removed_volume_m3", expectedRemovedM3,
                "actual_removed_volume_m3", actualRemovedM3, "relative_error", relativeError);
        }
        object AddMarkedSketchDimension(object target, object entity, string entityFace,
            string method, double x, double y, string label)
        {
            Call(target, "IModelDoc2", "ClearSelection2", true);
            if (!Convert.ToBoolean(Call(entity, entityFace, "Select4", false, null)))
                throw new Fault("DRIVING_DIMENSION_FAILED", "Cannot select geometry for driving dimension: " + label);
            object displayDimension = Call(target, "IModelDoc2", method, x, y, 0.0);
            if (displayDimension == null)
                throw new Fault("DRIVING_DIMENSION_FAILED", "SOLIDWORKS did not create driving dimension: " + label);
            NameDrivingDimension(displayDimension, label);
            Set(displayDimension, "IDisplayDimension", "MarkedForDrawing", true);
            if (!Convert.ToBoolean(Get(displayDimension, "IDisplayDimension", "MarkedForDrawing")))
                throw new Fault("DRIVING_DIMENSION_FAILED", "SOLIDWORKS did not mark the dimension for drawing: " + label);
            Call(target, "IModelDoc2", "ClearSelection2", true);
            return displayDimension;
        }
        object AddMarkedTwoPointDimension(object target, object firstPoint, object secondPoint,
            string method, double x, double y, string label)
        {
            Call(target, "IModelDoc2", "ClearSelection2", true);
            if (!Convert.ToBoolean(Call(firstPoint, "ISketchPoint", "Select4", false, null)) ||
                !Convert.ToBoolean(Call(secondPoint, "ISketchPoint", "Select4", true, null)))
                throw new Fault("DRIVING_DIMENSION_FAILED", "Cannot select both points for driving dimension: " + label);
            object displayDimension = Call(target, "IModelDoc2", method, x, y, 0.0);
            if (displayDimension == null)
                throw new Fault("DRIVING_DIMENSION_FAILED", "SOLIDWORKS did not create driving dimension: " + label);
            NameDrivingDimension(displayDimension, label);
            Set(displayDimension, "IDisplayDimension", "MarkedForDrawing", true);
            if (!Convert.ToBoolean(Get(displayDimension, "IDisplayDimension", "MarkedForDrawing")))
                throw new Fault("DRIVING_DIMENSION_FAILED", "SOLIDWORKS did not mark the dimension for drawing: " + label);
            Call(target, "IModelDoc2", "ClearSelection2", true);
            return displayDimension;
        }
        void NameDrivingDimension(object displayDimension, string name)
        {
            if (!ConnectorParameterName(name))
                throw new Fault("DRIVING_DIMENSION_FAILED", "Connector dimension names must use the AI_ prefix.");
            object dimension = Call(displayDimension, "IDisplayDimension", "GetDimension2", 0);
            if (dimension == null)
                throw new Fault("DRIVING_DIMENSION_FAILED", "Cannot obtain the created dimension before naming it: " + name);
            Set(dimension, "IDimension", "Name", name);
            if (!string.Equals(Text(Get(dimension, "IDimension", "Name")), name, StringComparison.Ordinal))
                throw new Fault("DRIVING_DIMENSION_FAILED", "SOLIDWORKS did not preserve the connector dimension name: " + name);
        }
        internal static bool SameSketchPoint(double x1, double y1, double x2, double y2)
        {
            return Math.Abs(x1 - x2) <= 1e-9 && Math.Abs(y1 - y2) <= 1e-9;
        }
        internal static int PlateDrivingDimensionCount(int holeCount)
        {
            return 3 + holeCount * 3;
        }
        Array ExtractCenterRectangleEdges(Array generatedSegments)
        {
            if (generatedSegments == null || generatedSegments.Length < 4)
                throw new Fault("SKETCH_FAILED", "CreateCenterRectangle did not return enough sketch segments.");

            // SOLIDWORKS returns both four profile edges and construction
            // diagonals for a centre rectangle. Only the non-construction edges
            // belong to the extrusion contour and can own length/width dimensions.
            var edges = new List<object>();
            foreach (object raw in generatedSegments)
            {
                object segment = Track(raw);
                bool construction = Convert.ToBoolean(Get(segment, "ISketchSegment", "ConstructionGeometry"));
                if (!construction) edges.Add(segment);
            }

            // Defensive fallback for templates that change construction flags:
            // the four outer edges are horizontal or vertical; the diagonals are not.
            if (edges.Count != 4)
            {
                edges.Clear();
                foreach (object raw in generatedSegments)
                {
                    object segment = Track(raw);
                    double angle = Convert.ToDouble(Get(segment, "ISketchLine", "Angle"), CultureInfo.InvariantCulture);
                    if (Math.Abs(Math.Sin(angle)) < 1e-7 || Math.Abs(Math.Cos(angle)) < 1e-7)
                        edges.Add(segment);
                }
            }
            if (edges.Count != 4)
                throw new Fault("SKETCH_FAILED", "Cannot identify the four profile edges returned by CreateCenterRectangle. returned=" +
                    generatedSegments.Length + ", profile_edges=" + edges.Count);
            return edges.ToArray();
        }
        object FindRectangleCorner(Array rectangleSegments, double expectedX, double expectedY)
        {
            foreach (object raw in rectangleSegments)
            {
                object line = Track(raw);
                foreach (string method in new[] { "GetStartPoint2", "GetEndPoint2" })
                {
                    object point = Call(line, "ISketchLine", method);
                    if (point == null) continue;
                    double x = Convert.ToDouble(Get(point, "ISketchPoint", "X"), CultureInfo.InvariantCulture);
                    double y = Convert.ToDouble(Get(point, "ISketchPoint", "Y"), CultureInfo.InvariantCulture);
                    if (SameSketchPoint(x, y, expectedX, expectedY)) return point;
                }
            }
            throw new Fault("DRIVING_DIMENSION_FAILED", "Cannot identify a rectangle corner for a hole-position dimension.");
        }
        object CreatePlateDrivingSketchDimensions(object target, Array rectangleSegments,
            IList<object> circleSegments, double halfX, double halfY)
        {
            object horizontal = null, vertical = null;
            foreach (object raw in rectangleSegments)
            {
                object segment = Track(raw);
                double angle = Convert.ToDouble(Get(segment, "ISketchLine", "Angle"), CultureInfo.InvariantCulture);
                if (horizontal == null && Math.Abs(Math.Sin(angle)) < 1e-7) horizontal = segment;
                if (vertical == null && Math.Abs(Math.Cos(angle)) < 1e-7) vertical = segment;
            }
            if (horizontal == null || vertical == null)
                throw new Fault("DRIVING_DIMENSION_FAILED", "Cannot identify the horizontal and vertical rectangle lines.");

            int inputPreference = EnumValue("swUserPreferenceToggle_e", "swInputDimValOnCreate");
            bool previousInputPreference = Convert.ToBoolean(Call(app, "ISldWorks", "GetUserPreferenceToggle", inputPreference));
            Call(app, "ISldWorks", "SetUserPreferenceToggle", inputPreference, false);
            try
            {
                AddMarkedSketchDimension(target, horizontal, "ISketchSegment", "AddHorizontalDimension2",
                    0.0, -halfY - 0.012, "AI_Length");
                AddMarkedSketchDimension(target, vertical, "ISketchSegment", "AddVerticalDimension2",
                    -halfX - 0.012, 0.0, "AI_Width");
                for (int i = 0; i < circleSegments.Count; i++)
                {
                    object circle = circleSegments[i];
                    object center = Call(circle, "ISketchArc", "GetCenterPoint2");
                    if (center == null) throw new Fault("DRIVING_DIMENSION_FAILED", "Cannot read a hole centre point.");
                    double x = Convert.ToDouble(Get(center, "ISketchPoint", "X"), CultureInfo.InvariantCulture);
                    double y = Convert.ToDouble(Get(center, "ISketchPoint", "Y"), CultureInfo.InvariantCulture);
                    AddMarkedSketchDimension(target, circle, "ISketchSegment", "AddDiameterDimension2",
                        x + 0.010, y + 0.010, "AI_Hole_Diameter_" + (i + 1));

                    double cornerX = x < 0.0 ? -halfX : halfX;
                    double cornerY = y < 0.0 ? -halfY : halfY;
                    object corner = FindRectangleCorner(rectangleSegments, cornerX, cornerY);
                    double displayOffset = 0.014 + i * 0.003;
                    AddMarkedTwoPointDimension(target, center, corner, "AddHorizontalDimension2",
                        (x + cornerX) / 2.0, cornerY + (cornerY < 0.0 ? -displayOffset : displayOffset),
                        "AI_Hole_Offset_X_" + (i + 1));
                    AddMarkedTwoPointDimension(target, center, corner, "AddVerticalDimension2",
                        cornerX + (cornerX < 0.0 ? -displayOffset : displayOffset), (y + cornerY) / 2.0,
                        "AI_Hole_Offset_Y_" + (i + 1));
                }
            }
            finally
            {
                Call(app, "ISldWorks", "SetUserPreferenceToggle", inputPreference, previousInputPreference);
            }
            return Json.Obj("status", "PASS", "count", 2 + circleSegments.Count * 3,
                "items", new[] { "AI_Length", "AI_Width", "AI_Hole_Diameter_1..4",
                    "AI_Hole_Offset_X_1..4", "AI_Hole_Offset_Y_1..4" },
                "marked_for_drawing", true,
                "position_dimension_reference", "Each hole centre is dimensioned horizontally and vertically to its nearest plate corner.");
        }
        object MarkExtrusionDimensionForDrawing(object target, object extrusion)
        {
            object extension = Get(target, "IModelDoc2", "Extension");
            int displayAnnotations = EnumValue("swUserPreferenceToggle_e", "swDisplayAnnotations");
            int displayFeatureDimensions = EnumValue("swUserPreferenceToggle_e", "swDisplayFeatureDimensions");
            int noOption = EnumValue("swUserPreferenceOption_e", "swDetailingNoOptionSpecified");
            bool previousAnnotations = Convert.ToBoolean(Call(extension, "IModelDocExtension",
                "GetUserPreferenceToggle", displayAnnotations, noOption));
            bool previousFeatureDimensions = Convert.ToBoolean(Call(extension, "IModelDocExtension",
                "GetUserPreferenceToggle", displayFeatureDimensions, noOption));
            try
            {
                Call(extension, "IModelDocExtension", "SetUserPreferenceToggle",
                    displayAnnotations, noOption, true);
                Call(extension, "IModelDocExtension", "SetUserPreferenceToggle",
                    displayFeatureDimensions, noOption, true);

                // GetFirstDisplayDimension can also return dimensions owned by the
                // extrusion's sketch, and SOLIDWORKS does not guarantee their order.
                // D1 is the extrusion depth parameter, so match its full model name
                // before marking anything for the drawing.
                object depthDimension = Call(extrusion, "IFeature", "Parameter", "D1");
                if (depthDimension == null)
                    throw new Fault("DRIVING_DIMENSION_FAILED", "Cannot obtain the extrusion D1 thickness parameter.");
                Set(depthDimension, "IDimension", "Name", "AI_Thickness");
                if (!string.Equals(Text(Get(depthDimension, "IDimension", "Name")), "AI_Thickness", StringComparison.Ordinal))
                    throw new Fault("DRIVING_DIMENSION_FAILED", "SOLIDWORKS did not preserve the AI_Thickness parameter name.");
                string expectedFullName = Text(Get(depthDimension, "IDimension", "FullName"));
                object displayDimension = Call(extrusion, "IFeature", "GetFirstDisplayDimension");
                object thicknessDisplayDimension = null;
                int guard = 0;
                while (displayDimension != null && guard++ < 100)
                {
                    object dimension = Call(displayDimension, "IDisplayDimension", "GetDimension2", 0);
                    string fullName = dimension == null ? null : Text(Get(dimension, "IDimension", "FullName"));
                    if (!string.IsNullOrEmpty(fullName) &&
                        string.Equals(fullName, expectedFullName, StringComparison.OrdinalIgnoreCase))
                    {
                        thicknessDisplayDimension = displayDimension;
                        break;
                    }
                    displayDimension = Call(extrusion, "IFeature", "GetNextDisplayDimension", displayDimension);
                }
                if (thicknessDisplayDimension == null)
                    throw new Fault("DRIVING_DIMENSION_FAILED", "Cannot locate the extrusion D1 display dimension.");
                Set(thicknessDisplayDimension, "IDisplayDimension", "MarkedForDrawing", true);
                if (!Convert.ToBoolean(Get(thicknessDisplayDimension, "IDisplayDimension", "MarkedForDrawing")))
                    throw new Fault("DRIVING_DIMENSION_FAILED", "Cannot mark the extrusion thickness for drawing.");
                return Json.Obj("status", "PASS", "count", 1, "item", "AI_Thickness",
                    "dimension_full_name", expectedFullName, "marked_for_drawing", true);
            }
            finally
            {
                Call(extension, "IModelDocExtension", "SetUserPreferenceToggle",
                    displayFeatureDimensions, noOption, previousFeatureDimensions);
                Call(extension, "IModelDocExtension", "SetUserPreferenceToggle",
                    displayAnnotations, noOption, previousAnnotations);
            }
        }
        object CreatePlate(Dictionary<string, object> args)
        {
            double lengthMm = Catalog.Real(args, "length_mm", 20, 2000);
            double widthMm = Catalog.Real(args, "width_mm", 20, 2000);
            double thicknessMm = Catalog.Real(args, "thickness_mm", 0.5, 200);
            double diameterMm = Catalog.Real(args, "hole_diameter_mm", 1, 200);
            double offsetXMm = Catalog.Real(args, "edge_offset_x_mm", 1, 1000);
            double offsetYMm = Catalog.Real(args, "edge_offset_y_mm", 1, 1000);

            object previous = Get(app, "ISldWorks", "IActiveDoc2");
            string previousTitle = previous == null ? null : Text(Call(previous, "IModelDoc2", "GetTitle"));
            string previousPath = previous == null ? null : Text(Call(previous, "IModelDoc2", "GetPathName"));
            bool? previousDirty = previous == null ? null : Bool(Call(previous, "IModelDoc2", "GetSaveFlag"));

            string templateSource;
            string template = FindPartTemplate(out templateSource);

            object created = null; string createdTitle = null; bool saved = false;
            try
            {
                created = Call(app, "ISldWorks", "NewDocument", template, 0, 0.0, 0.0);
                if (created == null) throw new Fault("CREATE_DOCUMENT_FAILED", "SOLIDWORKS did not create a new part document.");
                createdTitle = Text(Call(created, "IModelDoc2", "GetTitle"));
                if (Convert.ToInt32(Call(created, "IModelDoc2", "GetType")) != 1)
                    throw new Fault("WRONG_TEMPLATE_TYPE", "The configured default template did not create a part document.");

                Call(created, "IModelDoc2", "ClearSelection2", true);
                object feature = Call(created, "IModelDoc2", "IFirstFeature");
                object plane = null; int guard = 0;
                while (feature != null && guard++ < 100)
                {
                    if (Text(Call(feature, "IFeature", "GetTypeName2")) == "RefPlane") { plane = feature; break; }
                    feature = Call(feature, "IFeature", "GetNextFeature");
                }
                if (plane == null || !Convert.ToBoolean(Call(plane, "IFeature", "Select2", false, 0)))
                    throw new Fault("SKETCH_PLANE_NOT_FOUND", "Cannot select the first reference plane in the default part template.");

                var sketch = Get(created, "IModelDoc2", "SketchManager");
                Call(sketch, "ISketchManager", "InsertSketch", true);
                double halfX = lengthMm / 2000.0, halfY = widthMm / 2000.0;
                object rectangleRaw = Call(sketch, "ISketchManager", "CreateCenterRectangle", 0.0, 0.0, 0.0, halfX, halfY, 0.0);
                var generatedRectangleSegments = rectangleRaw as Array;
                if (generatedRectangleSegments == null)
                    throw new Fault("SKETCH_FAILED", "Cannot create the plate rectangle.");
                var rectangleSegments = ExtractCenterRectangleEdges(generatedRectangleSegments);
                double cx = halfX - offsetXMm / 1000.0;
                double cy = halfY - offsetYMm / 1000.0;
                double radius = diameterMm / 2000.0;
                var circleSegments = new List<object>();
                foreach (double sx in new[] { -1.0, 1.0 })
                    foreach (double sy in new[] { -1.0, 1.0 })
                    {
                        object circle = Call(sketch, "ISketchManager", "CreateCircleByRadius", sx * cx, sy * cy, 0.0, radius);
                        if (circle == null)
                            throw new Fault("SKETCH_FAILED", "Cannot create all four hole circles.");
                        circleSegments.Add(circle);
                    }
                object sketchDimensions = CreatePlateDrivingSketchDimensions(created, rectangleSegments,
                    circleSegments, halfX, halfY);
                Call(sketch, "ISketchManager", "InsertSketch", true);

                var features = Get(created, "IModelDoc2", "FeatureManager");
                object extrusion = Call(features, "IFeatureManager", "FeatureExtrusion2",
                    true, false, false, 0, 0, thicknessMm / 1000.0, thicknessMm / 1000.0,
                    false, false, false, false, 0.0, 0.0, false, false, false, false,
                    true, true, true, 0, 0.0, false);
                if (extrusion == null) throw new Fault("EXTRUSION_FAILED", "SOLIDWORKS did not create the plate extrusion.");
                object extrusionDimension = MarkExtrusionDimensionForDrawing(created, extrusion);
                Call(created, "IModelDoc2", "EditRebuild3");

                double actualVolume = VolumeOf(created);
                double expectedVolume = (lengthMm * widthMm - Math.PI * diameterMm * diameterMm) * thicknessMm * 1e-9;
                double volumeError = Math.Abs(actualVolume - expectedVolume) / expectedVolume;
                if (volumeError > 0.001)
                    throw new Fault("GEOMETRY_VERIFICATION_FAILED", "Generated volume differs from the requested four-hole plate by more than 0.1%. The file was not saved.");
                object topology = VerifyPrismaticCylinders(created, null,
                    new[] { diameterMm / 2.0, diameterMm / 2.0, diameterMm / 2.0, diameterMm / 2.0 });

                string outputDir = Program.EnsureWorkspace();
                string stem = "PLATE_" + FileNumber(lengthMm) + "x" + FileNumber(widthMm) + "x" + FileNumber(thicknessMm) +
                    "_4xD" + FileNumber(diameterMm) + "_" + DateTime.UtcNow.ToString("yyyyMMdd_HHmmss") + "_" + Guid.NewGuid().ToString("N").Substring(0, 8);
                string outputPath = Path.Combine(outputDir, stem + ".SLDPRT");
                // IModelDoc2.SaveAs3 has an obsolete, non-Boolean return contract. Use the
                // current extension API so success, errors and warnings are unambiguous.
                var saveExtension = Get(created, "IModelDoc2", "Extension");
                object[] saveArgs = { outputPath, 0, 1, null, null, 0, 0 };
                bool saveOk = Convert.ToBoolean(Call(saveExtension, "IModelDocExtension", "SaveAs3", saveArgs));
                int saveErrors = Convert.ToInt32(saveArgs[5], CultureInfo.InvariantCulture);
                int saveWarnings = Convert.ToInt32(saveArgs[6], CultureInfo.InvariantCulture);
                bool fileExists = File.Exists(outputPath);
                string confirmedPath = Text(Call(created, "IModelDoc2", "GetPathName"));
                bool pathConfirmed = !string.IsNullOrWhiteSpace(confirmedPath) &&
                    string.Equals(confirmedPath, outputPath, StringComparison.OrdinalIgnoreCase);
                if (!saveOk || saveErrors != 0 || !fileExists || !pathConfirmed)
                    throw new Fault("SAVE_FAILED", "SOLIDWORKS save failed. api_success=" + saveOk +
                        ", errors=" + saveErrors + ", warnings=" + saveWarnings + ", file_exists=" + fileExists +
                        ", confirmed_path=" + (confirmedPath ?? "<empty>") + ", requested_path=" + outputPath);
                saved = true;

                bool previousUnchanged = true;
                if (previous != null)
                    previousUnchanged = Text(Call(previous, "IModelDoc2", "GetTitle")) == previousTitle &&
                        Text(Call(previous, "IModelDoc2", "GetPathName")) == previousPath &&
                        Bool(Call(previous, "IModelDoc2", "GetSaveFlag")) == previousDirty;

                return Json.Obj("operation", "CREATED_NEW_PART", "connector_version", Program.Version,
                    "file_path", outputPath, "document_left_open", true, "material_assigned", false,
                    "template", Json.Obj("path", template, "source", templateSource),
                    "save", Json.Obj("method", "IModelDocExtension.SaveAs3", "api_success", saveOk,
                        "errors", saveErrors, "warnings", saveWarnings, "path_confirmed", pathConfirmed),
                    "parameters_mm", Json.Obj("length", lengthMm, "width", widthMm, "thickness", thicknessMm,
                        "hole_count", 4, "hole_diameter", diameterMm, "edge_offset_x", offsetXMm, "edge_offset_y", offsetYMm),
                    "driving_dimensions", Json.Obj("status", "PASS",
                        "total_marked_for_drawing", PlateDrivingDimensionCount(circleSegments.Count),
                        "sketch", sketchDimensions, "extrusion", extrusionDimension,
                        "scope", "Length, width, thickness, four hole diameters and eight hole-to-edge position dimensions are real SOLIDWORKS driving dimensions marked for drawing."),
                    "verification", Json.Obj("status", "PASS", "method", "IMassProperty.Volume", "expected_volume_m3", expectedVolume,
                        "actual_volume_m3", actualVolume, "relative_error", volumeError, "topology", topology),
                    "existing_document", Json.Obj("title", previousTitle, "path", previousPath, "unchanged", previousUnchanged),
                    "safety", "A new uniquely named SLDPRT was created. No save, rebuild, close or edit call was issued to the previously active document. Review the generated model before use.",
                    "manufacturing_approved", false);
            }
            catch
            {
                if (!saved && created != null && !string.IsNullOrEmpty(createdTitle))
                {
                    try { Call(app, "ISldWorks", "CloseDoc", createdTitle); } catch { }
                }
                throw;
            }
        }
        object CreatePartFromPlan(Dictionary<string, object> args)
        {
            PartPlan plan = PartPlan.Parse(args);

            object previous = Get(app, "ISldWorks", "IActiveDoc2");
            string previousTitle = previous == null ? null : Text(Call(previous, "IModelDoc2", "GetTitle"));
            string previousPath = previous == null ? null : Text(Call(previous, "IModelDoc2", "GetPathName"));
            bool? previousDirty = previous == null ? null : Bool(Call(previous, "IModelDoc2", "GetSaveFlag"));

            string templateSource;
            string template = FindPartTemplate(out templateSource);
            object created = null; string createdTitle = null; bool saved = false;
            try
            {
                created = Call(app, "ISldWorks", "NewDocument", template, 0, 0.0, 0.0);
                if (created == null) throw new Fault("CREATE_DOCUMENT_FAILED", "SOLIDWORKS did not create a new part document.");
                createdTitle = Text(Call(created, "IModelDoc2", "GetTitle"));
                if (Convert.ToInt32(Call(created, "IModelDoc2", "GetType")) != 1)
                    throw new Fault("WRONG_TEMPLATE_TYPE", "The selected template did not create a part document.");

                Call(created, "IModelDoc2", "ClearSelection2", true);
                object feature = Call(created, "IModelDoc2", "IFirstFeature");
                object plane = null; int guard = 0;
                while (feature != null && guard++ < 100)
                {
                    if (Text(Call(feature, "IFeature", "GetTypeName2")) == "RefPlane") { plane = feature; break; }
                    feature = Call(feature, "IFeature", "GetNextFeature");
                }
                if (plane == null || !Convert.ToBoolean(Call(plane, "IFeature", "Select2", false, 0)))
                    throw new Fault("SKETCH_PLANE_NOT_FOUND", "Cannot select the first reference plane in the part template.");

                var sketch = Get(created, "IModelDoc2", "SketchManager");
                Call(sketch, "ISketchManager", "InsertSketch", true);
                if (plan.ProfileType == "rectangle")
                {
                    object segments = Call(sketch, "ISketchManager", "CreateCenterRectangle", 0.0, 0.0, 0.0,
                        plan.WidthMm / 2000.0, plan.HeightMm / 2000.0, 0.0);
                    if (segments == null) throw new Fault("SKETCH_FAILED", "Cannot create the rectangular outer profile.");
                }
                else if (plan.ProfileType == "circle")
                {
                    if (Call(sketch, "ISketchManager", "CreateCircleByRadius", 0.0, 0.0, 0.0, plan.DiameterMm / 2000.0) == null)
                        throw new Fault("SKETCH_FAILED", "Cannot create the circular outer profile.");
                }
                else
                {
                    int pointCount = plan.Points.Count;
                    for (int i = 0; i < pointCount; i++)
                    {
                        PlanPoint a = plan.Points[i], b = plan.Points[(i + 1) % pointCount];
                        double startX = a.CornerStyle != null ? a.TangentOutXMm : a.X;
                        double startY = a.CornerStyle != null ? a.TangentOutYMm : a.Y;
                        double endX = b.CornerStyle != null ? b.TangentInXMm : b.X;
                        double endY = b.CornerStyle != null ? b.TangentInYMm : b.Y;
                        if (Call(sketch, "ISketchManager", "CreateLine", startX / 1000.0, startY / 1000.0, 0.0,
                            endX / 1000.0, endY / 1000.0, 0.0) == null)
                            throw new Fault("SKETCH_FAILED", "Cannot create every straight segment of the polygon outer profile.");
                    }
                    for (int i = 0; i < pointCount; i++)
                    {
                        PlanPoint corner = plan.Points[i];
                        if (corner.CornerStyle == null) continue;
                        object cornerSegment;
                        if (corner.CornerStyle == "chamfer")
                            cornerSegment = Call(sketch, "ISketchManager", "CreateLine",
                                corner.TangentInXMm / 1000.0, corner.TangentInYMm / 1000.0, 0.0,
                                corner.TangentOutXMm / 1000.0, corner.TangentOutYMm / 1000.0, 0.0);
                        else
                        {
                            double startAngle = Math.Atan2(
                                corner.TangentInYMm - corner.ArcCenterYMm,
                                corner.TangentInXMm - corner.ArcCenterXMm);
                            double endAngle = Math.Atan2(
                                corner.TangentOutYMm - corner.ArcCenterYMm,
                                corner.TangentOutXMm - corner.ArcCenterXMm);
                            double crossZ = (corner.TangentInXMm - corner.ArcCenterXMm) *
                                (corner.TangentOutYMm - corner.ArcCenterYMm) -
                                (corner.TangentInYMm - corner.ArcCenterYMm) *
                                (corner.TangentOutXMm - corner.ArcCenterXMm);
                            double sweep = endAngle - startAngle;
                            if (crossZ >= 0.0)
                                while (sweep <= 0.0) sweep += 2.0 * Math.PI;
                            else
                                while (sweep >= 0.0) sweep -= 2.0 * Math.PI;
                            cornerSegment = CreateThreePointSketchArc(sketch,
                                corner.ArcCenterXMm, corner.ArcCenterYMm,
                                corner.TangentInXMm / 1000.0, corner.TangentInYMm / 1000.0, 0.0,
                                corner.TangentOutXMm / 1000.0, corner.TangentOutYMm / 1000.0, 0.0,
                                startAngle, sweep);
                        }
                        if (cornerSegment == null)
                            throw new Fault("SKETCH_FAILED", "Cannot create every finished corner of the polygon outer profile.");
                    }
                }
                foreach (PlanHole hole in plan.Holes)
                    if (Call(sketch, "ISketchManager", "CreateCircleByRadius", hole.X / 1000.0, hole.Y / 1000.0, 0.0,
                        hole.Radius / 1000.0) == null)
                        throw new Fault("SKETCH_FAILED", "Cannot create every circular through hole.");
                Call(sketch, "ISketchManager", "InsertSketch", true);

                var features = Get(created, "IModelDoc2", "FeatureManager");
                object extrusion = Call(features, "IFeatureManager", "FeatureExtrusion2",
                    true, false, false, 0, 0, plan.ThicknessMm / 1000.0, plan.ThicknessMm / 1000.0,
                    false, false, false, false, 0.0, 0.0, false, false, false, false,
                    true, true, true, 0, 0.0, false);
                if (extrusion == null) throw new Fault("EXTRUSION_FAILED", "SOLIDWORKS did not extrude the validated profile.");
                Call(created, "IModelDoc2", "EditRebuild3");

                double baseVolume = VolumeOf(created);
                double baseVolumeError = Math.Abs(baseVolume - plan.BaseExpectedVolumeM3) / plan.BaseExpectedVolumeM3;
                if (baseVolumeError > 0.001)
                    throw new Fault("GEOMETRY_VERIFICATION_FAILED", "Generated base volume differs from the validated plan by more than 0.1%. The file was not saved.");
                var expectedHoleRadiiMm = new List<double>();
                foreach (PlanHole hole in plan.Holes) expectedHoleRadiiMm.Add(hole.Radius);
                var expectedOuterProfileRadiiMm = new List<double>();
                foreach (PlanPoint point in plan.Points)
                    if (point.CornerStyle == "round") expectedOuterProfileRadiiMm.Add(point.CornerSizeMm);
                object baseTopology = VerifyPrismaticCylinders(created,
                    plan.ProfileType == "circle" ? (double?)(plan.DiameterMm / 2.0) : null,
                    expectedHoleRadiiMm, null, null, expectedOuterProfileRadiiMm);

                var bossVerification = new List<object>();
                foreach (RectangularBoss boss in plan.RectangularBosses)
                {
                    double before = VolumeOf(created);
                    CreateRectangularBoss(created, boss);
                    double after = VolumeOf(created);
                    bossVerification.Add(VerifyAddedVolume(before, after,
                        boss.AreaMm2 * boss.Extrusion * 1e-9,
                        "rectangular_boss", boss.ToJson()));
                }
                foreach (CircularBoss boss in plan.CircularBosses)
                {
                    double before = VolumeOf(created);
                    CreateCircularBoss(created, boss);
                    double after = VolumeOf(created);
                    bossVerification.Add(VerifyAddedVolume(before, after,
                        boss.AreaMm2 * boss.Extrusion * 1e-9,
                        "circular_boss", boss.ToJson()));
                }
                double afterBossesVolume = VolumeOf(created);
                double afterBossesError = Math.Abs(afterBossesVolume - plan.ExpectedAfterBossesVolumeM3) /
                    plan.ExpectedAfterBossesVolumeM3;
                if (afterBossesError > 0.001)
                    throw new Fault("BOSS_VERIFICATION_FAILED", "The body volume after all bosses differs from the validated plan by more than 0.1%. The file was not saved.");

                var cutVerification = new List<object>();
                foreach (RectangularPocket pocket in plan.RectangularPockets)
                {
                    double before = VolumeOf(created);
                    CreateRectangularPocketCut(created, pocket);
                    double after = VolumeOf(created);
                    cutVerification.Add(VerifyCutVolume(before, after, pocket.AreaMm2 * pocket.Depth * 1e-9,
                        "rectangular_blind_pocket", pocket.ToJson()));
                }
                foreach (CircularPocket pocket in plan.CircularPockets)
                {
                    double before = VolumeOf(created);
                    CreateCircularPocketCut(created, pocket);
                    double after = VolumeOf(created);
                    cutVerification.Add(VerifyCutVolume(before, after, pocket.AreaMm2 * pocket.Depth * 1e-9,
                        "circular_blind_pocket", pocket.ToJson()));
                }
                foreach (StraightSlot slot in plan.StraightSlots)
                {
                    double before = VolumeOf(created);
                    CreateStraightSlotCut(created, slot);
                    double after = VolumeOf(created);
                    cutVerification.Add(VerifyCutVolume(before, after, slot.AreaMm2 * slot.Depth * 1e-9,
                        slot.Through ? "straight_through_slot" : "straight_blind_slot", slot.ToJson()));
                }

                double actualVolume = VolumeOf(created);
                double volumeError = Math.Abs(actualVolume - plan.ExpectedVolumeM3) / plan.ExpectedVolumeM3;
                if (volumeError > 0.001)
                    throw new Fault("GEOMETRY_VERIFICATION_FAILED", "Final volume differs from the validated plan by more than 0.1%. The file was not saved.");
                var additionalCutRadiiMm = new List<double>();
                foreach (CircularPocket pocket in plan.CircularPockets) additionalCutRadiiMm.Add(pocket.Radius);
                foreach (StraightSlot slot in plan.StraightSlots)
                { additionalCutRadiiMm.Add(slot.Radius); additionalCutRadiiMm.Add(slot.Radius); }
                var bossRadiiMm = new List<double>();
                foreach (CircularBoss boss in plan.CircularBosses) bossRadiiMm.Add(boss.Radius);
                foreach (RectangularBoss boss in plan.RectangularBosses)
                    if (boss.CornerStyle == "round")
                        for (int corner = 0; corner < 4; corner++) bossRadiiMm.Add(boss.CornerSize);
                object topology = VerifyPrismaticCylinders(created,
                    plan.ProfileType == "circle" ? (double?)(plan.DiameterMm / 2.0) : null,
                    expectedHoleRadiiMm, additionalCutRadiiMm, bossRadiiMm, expectedOuterProfileRadiiMm);

                object writtenProperties = ApplyPrismaticCreationProperties(created, plan);
                object assignedMaterial = ApplyAndVerifyMaterial(created, plan.MaterialName);

                string outputDir = Program.EnsureWorkspace();
                string stem = "AI_PART_" + plan.ProfileType.ToUpperInvariant() + "_" +
                    DateTime.UtcNow.ToString("yyyyMMdd_HHmmss") + "_" + Guid.NewGuid().ToString("N").Substring(0, 8);
                string outputPath = Path.Combine(outputDir, stem + ".SLDPRT");

                var saveExtension = Get(created, "IModelDoc2", "Extension");
                object[] saveArgs = { outputPath, 0, 1, null, null, 0, 0 };
                bool saveOk = Convert.ToBoolean(Call(saveExtension, "IModelDocExtension", "SaveAs3", saveArgs));
                int saveErrors = Convert.ToInt32(saveArgs[5], CultureInfo.InvariantCulture);
                int saveWarnings = Convert.ToInt32(saveArgs[6], CultureInfo.InvariantCulture);
                bool fileExists = File.Exists(outputPath);
                string confirmedPath = Text(Call(created, "IModelDoc2", "GetPathName"));
                bool pathConfirmed = !string.IsNullOrWhiteSpace(confirmedPath) &&
                    string.Equals(confirmedPath, outputPath, StringComparison.OrdinalIgnoreCase);
                if (!saveOk || saveErrors != 0 || !fileExists || !pathConfirmed)
                    throw new Fault("SAVE_FAILED", "SOLIDWORKS save failed. api_success=" + saveOk +
                        ", errors=" + saveErrors + ", warnings=" + saveWarnings + ", file_exists=" + fileExists +
                        ", confirmed_path=" + (confirmedPath ?? "<empty>") + ", requested_path=" + outputPath);
                saved = true;

                bool previousUnchanged = true;
                if (previous != null)
                    previousUnchanged = Text(Call(previous, "IModelDoc2", "GetTitle")) == previousTitle &&
                        Text(Call(previous, "IModelDoc2", "GetPathName")) == previousPath &&
                        Bool(Call(previous, "IModelDoc2", "GetSaveFlag")) == previousDirty;

                return Json.Obj("operation", "CREATED_NEW_PRISMATIC_PART", "connector_version", Program.Version,
                    "file_path", outputPath, "document_left_open", true, "material_assigned", assignedMaterial != null,
                    "plan", plan.ToJson(), "template", Json.Obj("path", template, "source", templateSource),
                    "written_properties", writtenProperties, "material", assignedMaterial,
                    "save", Json.Obj("method", "IModelDocExtension.SaveAs3", "api_success", saveOk,
                        "errors", saveErrors, "warnings", saveWarnings, "path_confirmed", pathConfirmed),
                    "verification", Json.Obj("status", "PASS", "method", "IMassProperty.Volume",
                        "expected_volume_m3", plan.ExpectedVolumeM3, "actual_volume_m3", actualVolume,
                        "relative_error", volumeError,
                        "base", Json.Obj("status", "PASS", "expected_volume_m3", plan.BaseExpectedVolumeM3,
                            "actual_volume_m3", baseVolume, "relative_error", baseVolumeError,
                            "topology", baseTopology),
                        "after_bosses", Json.Obj("status", "PASS",
                            "expected_volume_m3", plan.ExpectedAfterBossesVolumeM3,
                            "actual_volume_m3", afterBossesVolume, "relative_error", afterBossesError),
                        "bosses", bossVerification.ToArray(),
                        "cuts", cutVerification.ToArray(), "topology", topology),
                    "existing_document", Json.Obj("title", previousTitle, "path", previousPath, "unchanged", previousUnchanged),
                    "supported_scope", "Prismatic Plans v1-v5 remain compatible. Plan v6 adds selected chamfers or true rounds at convex polygon outer-profile vertices. Every outer round, boss, cut and final volume plus one-body and analytic-cylinder topology are verified. No stacked or overlapping bosses, top-edge bevels, threads or arbitrary COM.",
                    "safety", "A new uniquely named SLDPRT was created from validated numeric data. No save, rebuild, close or edit call was issued to the previously active document. Human review is required.",
                    "manufacturing_approved", false);
            }
            catch
            {
                if (!saved && created != null && !string.IsNullOrEmpty(createdTitle))
                {
                    try { Call(app, "ISldWorks", "CloseDoc", createdTitle); } catch { }
                }
                throw;
            }
        }

        object CreateThreePointSketchArc(object sketch, double centerXMm, double centerYMm,
            double startXMetres, double startYMetres, double startZMetres,
            double endXMetres, double endYMetres, double endZMetres,
            double startAngle, double signedSweepRadians)
        {
            double[] middle = ArcMidpointMetres(centerXMm, centerYMm,
                startXMetres, startYMetres, startAngle, signedSweepRadians);

            // Avoid the direction flag and its complementary-arc ambiguity. Three points
            // explicitly identify the requested sweep:
            // endpoint 1, endpoint 2 and a point that must lie on the requested sweep.
            return Call(sketch, "ISketchManager", "Create3PointArc",
                startXMetres, startYMetres, startZMetres,
                endXMetres, endYMetres, endZMetres,
                middle[0], middle[1], startZMetres);
        }

        object CreateCenterpointSketchArc(object sketch, double centerXMm, double centerYMm,
            double startXMm, double startYMm, double endXMm, double endYMm)
        {
            // CreateArc is unambiguous for an exact-radius quarter corner:
            // centre, start, end and Int16 direction. The first template plane's
            // normal reverses the direction relative to its displayed local XY,
            // therefore -1 produces the requested local quarter sweep. Passing
            // Int32 here breaks late-bound Interop with an Int32-to-Int16 error.
            return Call(sketch, "ISketchManager", "CreateArc",
                centerXMm / 1000.0, centerYMm / 1000.0, 0.0,
                startXMm / 1000.0, startYMm / 1000.0, 0.0,
                endXMm / 1000.0, endYMm / 1000.0, 0.0, (short)-1);
        }

        internal static double[] ArcMidpointMetres(double centerXMm, double centerYMm,
            double startXMetres, double startYMetres, double startAngle, double signedSweepRadians)
        {
            double centerXMetres = centerXMm / 1000.0;
            double centerYMetres = centerYMm / 1000.0;
            double radiusMetres = Math.Sqrt(
                (startXMetres - centerXMetres) * (startXMetres - centerXMetres) +
                (startYMetres - centerYMetres) * (startYMetres - centerYMetres));
            double middleAngle = startAngle + signedSweepRadians / 2.0;
            return new[] {
                centerXMetres + radiusMetres * Math.Cos(middleAngle),
                centerYMetres + radiusMetres * Math.Sin(middleAngle)
            };
        }

        void SketchContourLoop(object sketch, ContourLoop loop, string label)
        {
            foreach (ContourSegment segment in loop.Segments)
            {
                object created;
                if (segment.Type == "line")
                    created = Call(sketch, "ISketchManager", "CreateLine",
                        segment.Start.X / 1000.0, segment.Start.Y / 1000.0, 0.0,
                        segment.End.X / 1000.0, segment.End.Y / 1000.0, 0.0);
                else
                    created = CreateThreePointSketchArc(sketch,
                        segment.Center.X, segment.Center.Y,
                        segment.Start.X / 1000.0, segment.Start.Y / 1000.0, 0.0,
                        segment.End.X / 1000.0, segment.End.Y / 1000.0, 0.0,
                        Math.Atan2(segment.Start.Y - segment.Center.Y, segment.Start.X - segment.Center.X),
                        segment.SweepRadians);
                if (created == null) throw new Fault("SKETCH_FAILED", "Cannot create every line and arc of " + label + ".");
            }
        }

        object VerifyContourTopology(object target, ContourPartPlan plan)
        {
            int solidBody = EnumValue("swBodyType_e", "swSolidBody");
            var bodies = Call(target, "IPartDoc", "GetBodies2", solidBody, false) as Array;
            if (bodies == null || bodies.Length != 1)
                throw new Fault("GEOMETRY_TOPOLOGY_MISMATCH",
                    "The generated sheet-contour part must contain exactly one solid body. The file was not saved.");
            var actual = new List<double>();
            foreach (object body in bodies)
            {
                var faces = Call(body, "IBody2", "GetFaces") as Array;
                if (faces == null) continue;
                foreach (object face in faces)
                {
                    object surface = Call(face, "IFace2", "GetSurface");
                    if (surface == null || !Convert.ToBoolean(Call(surface, "ISurface", "IsCylinder"))) continue;
                    var values = Get(surface, "ISurface", "CylinderParams") as Array;
                    if (values == null || values.Length < 7)
                        throw new Fault("GEOMETRY_TOPOLOGY_MISMATCH", "A generated cylindrical face has no readable radius.");
                    actual.Add(Convert.ToDouble(values.GetValue(6), CultureInfo.InvariantCulture) * 1000.0);
                }
            }
            var expected = new List<double>();
            foreach (PlanHole hole in plan.Holes) expected.Add(hole.Radius);
            foreach (ContourSegment segment in plan.Outer.Segments)
                if (segment.Type == "arc") expected.Add(segment.RadiusMm);
            foreach (ContourLoop loop in plan.Inner)
                foreach (ContourSegment segment in loop.Segments)
                    if (segment.Type == "arc") expected.Add(segment.RadiusMm);
            if (!CylinderRadiiMatch(actual, null, expected))
                throw new Fault("GEOMETRY_TOPOLOGY_MISMATCH",
                    "Generated cylindrical faces do not match the validated contour arcs and holes. Expected " +
                    expected.Count + ", found " + actual.Count + ". The file was not saved.");
            actual.Sort();
            var diameters = new List<double>(); foreach (double radius in actual) diameters.Add(radius * 2.0);
            return Json.Obj("status", "PASS",
                "method", "ordered contour validation + IPartDoc.GetBodies2 + analytic cylindrical B-rep faces",
                "solid_body_count", bodies.Length, "outer_segment_count", plan.Outer.Segments.Count,
                "inner_contour_count", plan.Inner.Count, "through_hole_count", plan.Holes.Count,
                "expected_arc_and_hole_cylindrical_faces", expected.Count,
                "actual_cylindrical_face_count", actual.Count, "actual_diameters_mm", diameters.ToArray());
        }

        object ApplyContourCreationProperties(object target, ContourPartPlan plan)
        {
            var configurationManager = Get(target, "IModelDoc2", "ConfigurationManager");
            var activeConfiguration = Get(configurationManager, "IConfigurationManager", "ActiveConfiguration");
            string configurationName = Text(Get(activeConfiguration, "IConfiguration", "Name"));
            var extension = Get(target, "IModelDoc2", "Extension");
            var manager = Get(extension, "IModelDocExtension", "CustomPropertyManager", configurationName);
            int textType = EnumValue("swCustomInfoType_e", "swCustomInfoText");
            int replace = EnumValue("swCustomPropertyAddOption_e", "swCustomPropertyDeleteAndAdd");
            var written = new List<object>();
            if (plan.Properties != null)
            {
                if (plan.Properties.Designation != null)
                    written.Add(WriteAndVerifyProperty(manager, "Обозначение", plan.Properties.Designation, textType, replace));
                if (plan.Properties.Name != null)
                    written.Add(WriteAndVerifyProperty(manager, "Наименование", plan.Properties.Name, textType, replace));
            }
            written.Add(WriteAndVerifyProperty(manager, "AI_Тип_профиля", "sheet_contour", textType, replace));
            written.Add(WriteAndVerifyProperty(manager, "AI_Толщина_мм", plan.ThicknessMm.ToString("G17", CultureInfo.InvariantCulture), textType, replace));
            written.Add(WriteAndVerifyProperty(manager, "AI_Наружные_сегменты", plan.Outer.Segments.Count.ToString(CultureInfo.InvariantCulture), textType, replace));
            written.Add(WriteAndVerifyProperty(manager, "AI_Внутренние_контуры", plan.Inner.Count.ToString(CultureInfo.InvariantCulture), textType, replace));
            written.Add(WriteAndVerifyProperty(manager, "AI_Сквозные_отверстия", plan.Holes.Count.ToString(CultureInfo.InvariantCulture), textType, replace));
            return Json.Obj("configuration", configurationName, "items", written.ToArray(),
                "note", "Audited numeric contour data; manufacturing approval still requires human review.");
        }

        object CreateSheetFromContours(Dictionary<string, object> args)
        {
            ContourPartPlan plan = ContourPartPlan.Parse(args);
            object previous = Get(app, "ISldWorks", "IActiveDoc2");
            string previousTitle = previous == null ? null : Text(Call(previous, "IModelDoc2", "GetTitle"));
            string previousPath = previous == null ? null : Text(Call(previous, "IModelDoc2", "GetPathName"));
            bool? previousDirty = previous == null ? null : Bool(Call(previous, "IModelDoc2", "GetSaveFlag"));
            string templateSource;
            string template = FindPartTemplate(out templateSource);
            object created = null; string createdTitle = null; bool saved = false;
            try
            {
                created = Call(app, "ISldWorks", "NewDocument", template, 0, 0.0, 0.0);
                if (created == null) throw new Fault("CREATE_DOCUMENT_FAILED", "SOLIDWORKS did not create a new sheet-contour part.");
                createdTitle = Text(Call(created, "IModelDoc2", "GetTitle"));
                if (Convert.ToInt32(Call(created, "IModelDoc2", "GetType")) != 1)
                    throw new Fault("WRONG_TEMPLATE_TYPE", "The selected template did not create a part document.");
                object plane = FirstReferencePlane(created);
                if (!Convert.ToBoolean(Call(plane, "IFeature", "Select2", false, 0)))
                    throw new Fault("SKETCH_PLANE_NOT_FOUND", "Cannot select the first reference plane.");
                object sketch = Get(created, "IModelDoc2", "SketchManager");
                Call(sketch, "ISketchManager", "InsertSketch", true);
                SketchContourLoop(sketch, plan.Outer, "the validated outer contour");
                foreach (ContourLoop inner in plan.Inner)
                    SketchContourLoop(sketch, inner, "a validated inner contour");
                foreach (PlanHole hole in plan.Holes)
                    if (Call(sketch, "ISketchManager", "CreateCircleByRadius", hole.X / 1000.0,
                        hole.Y / 1000.0, 0.0, hole.Radius / 1000.0) == null)
                        throw new Fault("SKETCH_FAILED", "Cannot create every validated through hole.");
                Call(sketch, "ISketchManager", "InsertSketch", true);
                object features = Get(created, "IModelDoc2", "FeatureManager");
                object extrusion = Call(features, "IFeatureManager", "FeatureExtrusion2",
                    true, false, false, 0, 0, plan.ThicknessMm / 1000.0, plan.ThicknessMm / 1000.0,
                    false, false, false, false, 0.0, 0.0, false, false, false, false,
                    true, true, true, 0, 0.0, false);
                if (extrusion == null) throw new Fault("EXTRUSION_FAILED", "SOLIDWORKS did not extrude the validated sheet contours.");
                Call(created, "IModelDoc2", "EditRebuild3");
                double actualVolume = VolumeOf(created);
                double relativeError = Math.Abs(actualVolume - plan.ExpectedVolumeM3) / plan.ExpectedVolumeM3;
                if (relativeError > 0.001)
                    throw new Fault("GEOMETRY_VERIFICATION_FAILED", "Generated sheet volume differs from the validated contour plan by more than 0.1%. The file was not saved.");
                object topology = VerifyContourTopology(created, plan);
                object writtenProperties = ApplyContourCreationProperties(created, plan);
                object material = ApplyAndVerifyMaterial(created, plan.MaterialName);
                string outputDir = Program.EnsureWorkspace();
                string stem = "AI_SHEET_CONTOUR_" + DateTime.UtcNow.ToString("yyyyMMdd_HHmmss") + "_" + Guid.NewGuid().ToString("N").Substring(0, 8);
                string outputPath = Path.Combine(outputDir, stem + ".SLDPRT");
                object extension = Get(created, "IModelDoc2", "Extension");
                object[] saveArgs = { outputPath, 0, 1, null, null, 0, 0 };
                bool saveOk = Convert.ToBoolean(Call(extension, "IModelDocExtension", "SaveAs3", saveArgs));
                int saveErrors = Convert.ToInt32(saveArgs[5], CultureInfo.InvariantCulture);
                int saveWarnings = Convert.ToInt32(saveArgs[6], CultureInfo.InvariantCulture);
                string confirmedPath = Text(Call(created, "IModelDoc2", "GetPathName"));
                bool pathConfirmed = string.Equals(confirmedPath, outputPath, StringComparison.OrdinalIgnoreCase);
                if (!saveOk || saveErrors != 0 || !File.Exists(outputPath) || !pathConfirmed)
                    throw new Fault("SAVE_FAILED", "SOLIDWORKS did not save the generated sheet-contour part.");
                saved = true;
                bool previousUnchanged = previous == null ||
                    (Text(Call(previous, "IModelDoc2", "GetTitle")) == previousTitle &&
                     Text(Call(previous, "IModelDoc2", "GetPathName")) == previousPath &&
                     Bool(Call(previous, "IModelDoc2", "GetSaveFlag")) == previousDirty);
                return Json.Obj("operation", "CREATED_NEW_SHEET_CONTOUR_PART", "connector_version", Program.Version,
                    "file_path", outputPath, "document_left_open", true, "plan", plan.ToJson(),
                    "template", Json.Obj("path", template, "source", templateSource),
                    "written_properties", writtenProperties, "material", material,
                    "save", Json.Obj("method", "IModelDocExtension.SaveAs3", "api_success", saveOk,
                        "errors", saveErrors, "warnings", saveWarnings, "path_confirmed", pathConfirmed),
                    "verification", Json.Obj("status", "PASS", "expected_volume_m3", plan.ExpectedVolumeM3,
                        "actual_volume_m3", actualVolume, "relative_error", relativeError, "topology", topology),
                    "existing_document", Json.Obj("title", previousTitle, "path", previousPath, "unchanged", previousUnchanged),
                    "supported_scope", "Flat constant-thickness parts defined by ordered closed line/arc contours, optional inner cutouts, explicit holes and linear hole patterns. No bends, formed sheet-metal features, angle/channel/tube members, countersinks or threads.",
                    "safety", "A new uniquely named SLDPRT was created in local Workspace. Existing documents were not saved, rebuilt, closed or edited. Human review is required.",
                    "manufacturing_approved", false);
            }
            catch
            {
                if (!saved && created != null && !string.IsNullOrEmpty(createdTitle))
                    try { Call(app, "ISldWorks", "CloseDoc", createdTitle); } catch { }
                throw;
            }
        }
        object SketchLine(object sketch, double x1Mm, double y1Mm, double x2Mm, double y2Mm, string label)
        {
            object segment = Call(sketch, "ISketchManager", "CreateLine", x1Mm / 1000.0, y1Mm / 1000.0, 0.0,
                x2Mm / 1000.0, y2Mm / 1000.0, 0.0);
            if (segment == null) throw new Fault("SKETCH_FAILED", "Cannot create " + label + ".");
            return segment;
        }
        object ReferencePlane(object target, int index)
        {
            Call(target, "IModelDoc2", "ClearSelection2", true);
            object feature = Call(target, "IModelDoc2", "IFirstFeature");
            int guard = 0, found = 0;
            while (feature != null && guard++ < 100)
            {
                if (Text(Call(feature, "IFeature", "GetTypeName2")) == "RefPlane")
                {
                    if (found == index) return feature;
                    found++;
                }
                feature = Call(feature, "IFeature", "GetNextFeature");
            }
            throw new Fault("SKETCH_PLANE_NOT_FOUND", "Cannot find reference plane index " + index + " in the part template.");
        }
        object FirstReferencePlane(object target) { return ReferencePlane(target, 0); }

        void SketchClosedPolygon(object sketch, List<double[]> points, string label)
        {
            if (points == null || points.Count < 3) throw new Fault("SKETCH_FAILED", "Invalid polygon for " + label + ".");
            for (int i = 0; i < points.Count; i++)
            {
                double[] a = points[i], b = points[(i + 1) % points.Count];
                SketchLine(sketch, a[0], a[1], b[0], b[1], label);
            }
        }

        void SketchSplineGrooves(object sketch, LongitudinalSplineZone spline)
        {
            double pitch = 2.0 * Math.PI / spline.ToothCount;
            double halfWidth = spline.ToothWidth / 2.0;
            double rootHalf = Math.Asin(halfWidth / spline.RootRadius);
            double outsideRadius = spline.TipRadius + 2.0;
            double outsideHalf = Math.Asin(halfWidth / outsideRadius);
            double phase = spline.PhaseDegrees * Math.PI / 180.0;
            const int outerSegments = 4;
            const int innerSegments = 12;

            for (int tooth = 0; tooth < spline.ToothCount; tooth++)
            {
                double center = phase + tooth * pitch;
                double innerStart = center + rootHalf;
                double innerEnd = center + pitch - rootHalf;
                double outerStart = center + outsideHalf;
                double outerEnd = center + pitch - outsideHalf;
                var points = new List<double[]>();
                points.Add(new[] { spline.RootRadius * Math.Cos(innerStart), spline.RootRadius * Math.Sin(innerStart) });
                points.Add(new[] { outsideRadius * Math.Cos(outerStart), outsideRadius * Math.Sin(outerStart) });
                for (int i = 1; i <= outerSegments; i++)
                {
                    double a = outerStart + (outerEnd - outerStart) * i / outerSegments;
                    points.Add(new[] { outsideRadius * Math.Cos(a), outsideRadius * Math.Sin(a) });
                }
                points.Add(new[] { spline.RootRadius * Math.Cos(innerEnd), spline.RootRadius * Math.Sin(innerEnd) });
                double step = (innerEnd - innerStart) / innerSegments;
                double tangentRadius = spline.RootRadius / Math.Cos(step / 2.0);
                for (int i = 1; i < innerSegments; i++)
                {
                    double a = innerEnd - step * i;
                    points.Add(new[] { tangentRadius * Math.Cos(a), tangentRadius * Math.Sin(a) });
                }
                SketchClosedPolygon(sketch, points, "a validated longitudinal spline groove");
            }
        }

        object ApplyNewPartProperties(object target, NewPartProperties values)
        {
            if (values == null) return null;
            var configurationManager = Get(target, "IModelDoc2", "ConfigurationManager");
            var activeConfiguration = Get(configurationManager, "IConfigurationManager", "ActiveConfiguration");
            string configurationName = Text(Get(activeConfiguration, "IConfiguration", "Name"));
            var extension = Get(target, "IModelDoc2", "Extension");
            var manager = Get(extension, "IModelDocExtension", "CustomPropertyManager", configurationName);
            int textType = EnumValue("swCustomInfoType_e", "swCustomInfoText");
            int replace = EnumValue("swCustomPropertyAddOption_e", "swCustomPropertyDeleteAndAdd");
            var written = new List<object>();
            if (values.Designation != null) written.Add(WriteAndVerifyProperty(manager, "Обозначение", values.Designation, textType, replace));
            if (values.Name != null) written.Add(WriteAndVerifyProperty(manager, "Наименование", values.Name, textType, replace));
            return Json.Obj("configuration", configurationName, "items", written.ToArray());
        }

        object ApplyPrismaticCreationProperties(object target, PartPlan plan)
        {
            if (plan.PlanVersion == PartPlan.BasicVersion) return null;
            var configurationManager = Get(target, "IModelDoc2", "ConfigurationManager");
            var activeConfiguration = Get(configurationManager, "IConfigurationManager", "ActiveConfiguration");
            string configurationName = Text(Get(activeConfiguration, "IConfiguration", "Name"));
            var extension = Get(target, "IModelDoc2", "Extension");
            var manager = Get(extension, "IModelDocExtension", "CustomPropertyManager", configurationName);
            int textType = EnumValue("swCustomInfoType_e", "swCustomInfoText");
            int replace = EnumValue("swCustomPropertyAddOption_e", "swCustomPropertyDeleteAndAdd");
            var written = new List<object>();
            if (plan.Properties != null)
            {
                if (plan.Properties.Designation != null)
                    written.Add(WriteAndVerifyProperty(manager, "Обозначение", plan.Properties.Designation, textType, replace));
                if (plan.Properties.Name != null)
                    written.Add(WriteAndVerifyProperty(manager, "Наименование", plan.Properties.Name, textType, replace));
            }
            written.Add(WriteAndVerifyProperty(manager, "AI_Тип_профиля", plan.ProfileType, textType, replace));
            written.Add(WriteAndVerifyProperty(manager, "AI_Толщина_мм",
                plan.ThicknessMm.ToString("G17", CultureInfo.InvariantCulture), textType, replace));
            if (plan.ProfileType == "circle")
                written.Add(WriteAndVerifyProperty(manager, "AI_Наружный_диаметр_мм",
                    plan.DiameterMm.ToString("G17", CultureInfo.InvariantCulture), textType, replace));
            else if (plan.ProfileType == "rectangle")
            {
                written.Add(WriteAndVerifyProperty(manager, "AI_Ширина_мм",
                    plan.WidthMm.ToString("G17", CultureInfo.InvariantCulture), textType, replace));
                written.Add(WriteAndVerifyProperty(manager, "AI_Высота_мм",
                    plan.HeightMm.ToString("G17", CultureInfo.InvariantCulture), textType, replace));
            }
            if (plan.Pattern != null)
            {
                written.Add(WriteAndVerifyProperty(manager, "AI_Диаметр_окружности_отверстий_мм",
                    plan.Pattern.PitchCircleDiameter.ToString("G17", CultureInfo.InvariantCulture), textType, replace));
                written.Add(WriteAndVerifyProperty(manager, "AI_Диаметр_отверстий_мм",
                    plan.Pattern.HoleDiameter.ToString("G17", CultureInfo.InvariantCulture), textType, replace));
                written.Add(WriteAndVerifyProperty(manager, "AI_Количество_отверстий",
                    plan.Pattern.HoleCount.ToString(CultureInfo.InvariantCulture), textType, replace));
                written.Add(WriteAndVerifyProperty(manager, "AI_Начальный_угол_град",
                    plan.Pattern.StartAngleDegrees.ToString("G17", CultureInfo.InvariantCulture), textType, replace));
            }
            if (plan.PlanVersion == PartPlan.CutVersion || plan.PlanVersion == PartPlan.BossVersion ||
                plan.PlanVersion == PartPlan.CornerBossVersion || plan.PlanVersion == PartPlan.FilletVersion)
            {
                written.Add(WriteAndVerifyProperty(manager, "AI_Прямоугольные_карманы",
                    plan.RectangularPockets.Count.ToString(CultureInfo.InvariantCulture), textType, replace));
                written.Add(WriteAndVerifyProperty(manager, "AI_Круглые_карманы",
                    plan.CircularPockets.Count.ToString(CultureInfo.InvariantCulture), textType, replace));
                written.Add(WriteAndVerifyProperty(manager, "AI_Прямые_пазы",
                    plan.StraightSlots.Count.ToString(CultureInfo.InvariantCulture), textType, replace));
            }
            if (plan.PlanVersion == PartPlan.BossVersion || plan.PlanVersion == PartPlan.CornerBossVersion ||
                plan.PlanVersion == PartPlan.FilletVersion)
            {
                written.Add(WriteAndVerifyProperty(manager, "AI_Прямоугольные_выступы",
                    plan.RectangularBosses.Count.ToString(CultureInfo.InvariantCulture), textType, replace));
                written.Add(WriteAndVerifyProperty(manager, "AI_Круглые_выступы",
                    plan.CircularBosses.Count.ToString(CultureInfo.InvariantCulture), textType, replace));
            }
            if (plan.PlanVersion == PartPlan.CornerBossVersion || plan.PlanVersion == PartPlan.FilletVersion)
            {
                int chamferedCorners = 0, roundedCorners = 0;
                foreach (RectangularBoss boss in plan.RectangularBosses)
                {
                    if (boss.CornerStyle == "chamfer") chamferedCorners += 4;
                    if (boss.CornerStyle == "round") roundedCorners += 4;
                }
                written.Add(WriteAndVerifyProperty(manager, "AI_Угловые_фаски",
                    chamferedCorners.ToString(CultureInfo.InvariantCulture), textType, replace));
                written.Add(WriteAndVerifyProperty(manager, "AI_Угловые_скругления",
                    roundedCorners.ToString(CultureInfo.InvariantCulture), textType, replace));
            }
            return Json.Obj("configuration", configurationName, "items", written.ToArray(),
                "note", "These are audited creation parameters. They do not claim that the saved sketch is fully constrained.");
        }

        object ApplyAndVerifyMaterial(object target, string materialName)
        {
            if (materialName == null) return null;
            var configurationManager = Get(target, "IModelDoc2", "ConfigurationManager");
            var activeConfiguration = Get(configurationManager, "IConfigurationManager", "ActiveConfiguration");
            string configurationName = Text(Get(activeConfiguration, "IConfiguration", "Name"));
            var databases = new List<string>();
            databases.Add("");
            try
            {
                Array available = Call(app, "ISldWorks", "GetMaterialDatabases") as Array;
                if (available != null)
                    foreach (object item in available)
                    {
                        string database = Text(item);
                        if (!string.IsNullOrWhiteSpace(database) && !databases.Contains(database)) databases.Add(database);
                    }
            }
            catch { }

            Exception lastError = null;
            foreach (string database in databases)
            {
                try
                {
                    Call(target, "IPartDoc", "SetMaterialPropertyName2", configurationName, database, materialName);
                    object[] getArgs = { configurationName, null };
                    string actualName = Text(Call(target, "IPartDoc", "GetMaterialPropertyName2", getArgs));
                    string actualDatabase = Text(getArgs[1]);
                    if (string.Equals(actualName, materialName, StringComparison.OrdinalIgnoreCase))
                        return Json.Obj("name", actualName, "database", actualDatabase,
                            "configuration", configurationName, "verified", true,
                            "source", "IPartDoc.SetMaterialPropertyName2 + GetMaterialPropertyName2");
                }
                catch (Exception ex) { lastError = ex; }
            }
            string detail = lastError == null ? "SOLIDWORKS did not confirm the requested material." : Program.Unwrap(lastError)["message"].ToString();
            throw new Fault("MATERIAL_ASSIGNMENT_FAILED", "Cannot assign and verify material " + materialName + ". " + detail);
        }

        object WriteAndVerifyProperty(object manager, string name, string value, int textType, int replace)
        {
            Call(manager, "ICustomPropertyManager", "Add3", name, textType, value, replace);
            object[] getArgs = { name, true, "", "", false, false };
            Call(manager, "ICustomPropertyManager", "Get6", getArgs);
            string raw = Text(getArgs[2]), resolved = Text(getArgs[3]);
            if (!string.Equals(raw, value, StringComparison.Ordinal) && !string.Equals(resolved, value, StringComparison.Ordinal))
                throw new Fault("PROPERTY_WRITE_FAILED", "SOLIDWORKS did not confirm the new-part property: " + name);
            return Json.Obj("name", name, "value", value, "verified", true);
        }
        object ApproximateBox(object target)
        {
            var a = Call(target, "IPartDoc", "GetPartBox", true) as Array;
            if (a == null || a.Length != 6) return null;
            double[] v = new double[6];
            for (int i = 0; i < 6; i++) v[i] = Convert.ToDouble(a.GetValue(i), CultureInfo.InvariantCulture);
            return new[] { Math.Abs(v[3] - v[0]) * 1000.0, Math.Abs(v[4] - v[1]) * 1000.0,
                Math.Abs(v[5] - v[2]) * 1000.0 };
        }
        object CreateTurnedPartFromPlan(Dictionary<string, object> args)
        {
            TurnedPartPlan plan = TurnedPartPlan.Parse(args);
            double axisShiftMm = plan.Spline == null ? 0.0 : plan.Spline.MidX;

            object previous = Get(app, "ISldWorks", "IActiveDoc2");
            string previousTitle = previous == null ? null : Text(Call(previous, "IModelDoc2", "GetTitle"));
            string previousPath = previous == null ? null : Text(Call(previous, "IModelDoc2", "GetPathName"));
            bool? previousDirty = previous == null ? null : Bool(Call(previous, "IModelDoc2", "GetSaveFlag"));

            string templateSource;
            string template = FindPartTemplate(out templateSource);
            object created = null; string createdTitle = null; bool saved = false;
            try
            {
                created = Call(app, "ISldWorks", "NewDocument", template, 0, 0.0, 0.0);
                if (created == null) throw new Fault("CREATE_DOCUMENT_FAILED", "SOLIDWORKS did not create a new part document.");
                createdTitle = Text(Call(created, "IModelDoc2", "GetTitle"));
                if (Convert.ToInt32(Call(created, "IModelDoc2", "GetType")) != 1)
                    throw new Fault("WRONG_TEMPLATE_TYPE", "The selected template did not create a part document.");

                object plane = FirstReferencePlane(created);
                if (!Convert.ToBoolean(Call(plane, "IFeature", "Select2", false, 0)))
                    throw new Fault("SKETCH_PLANE_NOT_FOUND", "Cannot select the first reference plane for the turned profile.");
                var sketch = Get(created, "IModelDoc2", "SketchManager");
                Call(sketch, "ISketchManager", "InsertSketch", true);

                TurnedProfilePoint firstOuter = plan.Outer[0];
                SketchLine(sketch, firstOuter.X - axisShiftMm, 0.0,
                    firstOuter.X - axisShiftMm, firstOuter.Radius, "the outer-profile start");
                for (int i = 1; i < plan.Outer.Count; i++)
                {
                    TurnedProfilePoint a = plan.Outer[i - 1], b = plan.Outer[i];
                    SketchLine(sketch, a.X - axisShiftMm, a.Radius,
                        b.X - axisShiftMm, b.Radius, "every outer-profile segment");
                }

                TurnedProfilePoint lastOuter = plan.Outer[plan.Outer.Count - 1];
                object axisSegment;
                if (plan.Bore.Count == 0)
                {
                    SketchLine(sketch, lastOuter.X - axisShiftMm, lastOuter.Radius,
                        plan.LengthMm - axisShiftMm, 0.0, "the end face");
                    axisSegment = SketchLine(sketch, plan.LengthMm - axisShiftMm, 0.0,
                        -axisShiftMm, 0.0, "the revolve axis");
                }
                else
                {
                    TurnedProfilePoint lastBore = plan.Bore[plan.Bore.Count - 1];
                    SketchLine(sketch, lastOuter.X - axisShiftMm, lastOuter.Radius,
                        lastBore.X - axisShiftMm, lastBore.Radius, "the bored end face");
                    for (int i = plan.Bore.Count - 1; i > 0; i--)
                    {
                        TurnedProfilePoint a = plan.Bore[i], b = plan.Bore[i - 1];
                        SketchLine(sketch, a.X - axisShiftMm, a.Radius,
                            b.X - axisShiftMm, b.Radius, "every axial-bore segment");
                    }
                    TurnedProfilePoint tip = plan.Bore[0];
                    axisSegment = SketchLine(sketch, tip.X - axisShiftMm, 0.0,
                        -axisShiftMm, 0.0, "the revolve axis");
                }
                Call(sketch, "ISketchManager", "InsertSketch", true);

                var selection = Get(created, "IModelDoc2", "SelectionManager");
                var selectData = Call(selection, "ISelectionMgr", "CreateSelectData");
                Set(selectData, "ISelectData", "Mark", 16);
                if (!Convert.ToBoolean(Call(axisSegment, "ISketchSegment", "Select4", true, selectData)))
                    throw new Fault("REVOLVE_AXIS_SELECTION_FAILED", "Cannot select the validated profile axis.");

                var features = Get(created, "IModelDoc2", "FeatureManager");
                object revolve = Call(features, "IFeatureManager", "FeatureRevolve2",
                    true, true, false, false, false, false, 0, 0, 2.0 * Math.PI, 0.0,
                    false, false, 0.01, 0.01, 0, 0.0, 0.0, true, true, true);
                if (revolve == null) throw new Fault("REVOLVE_FAILED", "SOLIDWORKS did not revolve the validated axial profile.");
                Call(created, "IModelDoc2", "EditRebuild3");

                double revolvedVolume = VolumeOf(created);
                double revolvedError = Math.Abs(revolvedVolume - plan.AxisymmetricVolumeM3) / plan.AxisymmetricVolumeM3;
                if (revolvedError > 0.001)
                    throw new Fault("GEOMETRY_VERIFICATION_FAILED", "The revolved body volume differs from the validated axial profile by more than 0.1%. The file was not saved.");

                double splineVolume = revolvedVolume;
                if (plan.Spline != null)
                {
                    Call(created, "IModelDoc2", "ClearSelection2", true);
                    object crossPlane = ReferencePlane(created, 2);
                    if (!Convert.ToBoolean(Call(crossPlane, "IFeature", "Select2", false, 0)))
                        throw new Fault("SKETCH_PLANE_NOT_FOUND", "Cannot select the transverse reference plane for spline grooves.");
                    Call(sketch, "ISketchManager", "InsertSketch", true);
                    SketchSplineGrooves(sketch, plan.Spline);
                    Call(sketch, "ISketchManager", "InsertSketch", true);

                    double halfLength = (plan.Spline.EndX - plan.Spline.StartX) / 2000.0;
                    object splineCut = Call(features, "IFeatureManager", "FeatureCut4",
                        false, false, false, 0, 0, halfLength, halfLength,
                        false, false, false, false, 0.0, 0.0, false, false, false, false,
                        false, true, true, false, false, false, 0, 0.0, false, false);
                    if (splineCut == null)
                        throw new Fault("SPLINE_CUT_FAILED", "SOLIDWORKS did not create the validated longitudinal spline grooves.");
                    Call(created, "IModelDoc2", "EditRebuild3");
                    splineVolume = VolumeOf(created);
                    if (splineVolume >= revolvedVolume - 1e-12)
                        throw new Fault("GEOMETRY_VERIFICATION_FAILED", "Spline grooves did not remove measurable material. The file was not saved.");
                }

                bool hasRadialCuts = plan.RadialHoles.Count > 0 || plan.SideSlots.Count > 0;
                if (hasRadialCuts)
                {
                    Call(created, "IModelDoc2", "ClearSelection2", true);
                    if (!Convert.ToBoolean(Call(plane, "IFeature", "Select2", false, 0)))
                        throw new Fault("SKETCH_PLANE_NOT_FOUND", "Cannot reselect the reference plane for radial cuts.");
                    Call(sketch, "ISketchManager", "InsertSketch", true);
                    foreach (RadialHole hole in plan.RadialHoles)
                        if (Call(sketch, "ISketchManager", "CreateCircleByRadius", (hole.X - axisShiftMm) / 1000.0, 0.0, 0.0,
                            hole.Radius / 1000.0) == null)
                            throw new Fault("SKETCH_FAILED", "Cannot create every radial-hole circle.");
                    foreach (SideFlatSlot slot in plan.SideSlots)
                    {
                        double outside = plan.MaximumDiameterMm / 2.0 + 2.0;
                        double y0 = slot.Side == "positive" ? slot.FloorRadius : -outside;
                        double y1 = slot.Side == "positive" ? outside : -slot.FloorRadius;
                        SketchLine(sketch, slot.StartX - axisShiftMm, y0, slot.EndX - axisShiftMm, y0, "a side-slot floor");
                        SketchLine(sketch, slot.EndX - axisShiftMm, y0, slot.EndX - axisShiftMm, y1, "a side-slot wall");
                        SketchLine(sketch, slot.EndX - axisShiftMm, y1, slot.StartX - axisShiftMm, y1, "a side-slot outside edge");
                        SketchLine(sketch, slot.StartX - axisShiftMm, y1, slot.StartX - axisShiftMm, y0, "a side-slot wall");
                    }
                    Call(sketch, "ISketchManager", "InsertSketch", true);

                    int throughAll = EnumValue("swEndConditions_e", "swEndCondThroughAll");
                    int sketchPlane = EnumValue("swStartConditions_e", "swStartSketchPlane");
                    object cut = Call(features, "IFeatureManager", "FeatureCut4",
                        false, false, false, throughAll, throughAll, 0.01, 0.01,
                        false, false, false, false, 0.0, 0.0, false, false, false, false,
                        false, true, true, false, false, false, sketchPlane, 0.0, false, false);
                    if (cut == null) throw new Fault("RADIAL_CUT_FAILED", "SOLIDWORKS did not create the validated radial holes and side slots.");
                    Call(created, "IModelDoc2", "EditRebuild3");
                }

                double finalVolume = VolumeOf(created);
                if (hasRadialCuts && finalVolume >= splineVolume - 1e-12)
                    throw new Fault("GEOMETRY_VERIFICATION_FAILED", "Radial cuts did not remove measurable material. The file was not saved.");
                double? referenceError = null;
                if (plan.ReferenceVolumeM3.HasValue)
                {
                    referenceError = Math.Abs(finalVolume - plan.ReferenceVolumeM3.Value) / plan.ReferenceVolumeM3.Value;
                    if (referenceError.Value > TurnedPartPlan.ReferenceTolerance)
                        throw new Fault("REFERENCE_VOLUME_MISMATCH", "Generated volume differs from the supplied reference by more than 0.05%. The file was not saved.");
                }

                object writtenProperties = ApplyNewPartProperties(created, plan.Properties);

                string outputDir = Program.EnsureWorkspace();
                string outputPath = Path.Combine(outputDir, "AI_TURNED_PART_" + DateTime.UtcNow.ToString("yyyyMMdd_HHmmss") +
                    "_" + Guid.NewGuid().ToString("N").Substring(0, 8) + ".SLDPRT");

                var saveExtension = Get(created, "IModelDoc2", "Extension");
                object[] saveArgs = { outputPath, 0, 1, null, null, 0, 0 };
                bool saveOk = Convert.ToBoolean(Call(saveExtension, "IModelDocExtension", "SaveAs3", saveArgs));
                int saveErrors = Convert.ToInt32(saveArgs[5], CultureInfo.InvariantCulture);
                int saveWarnings = Convert.ToInt32(saveArgs[6], CultureInfo.InvariantCulture);
                bool fileExists = File.Exists(outputPath);
                string confirmedPath = Text(Call(created, "IModelDoc2", "GetPathName"));
                bool pathConfirmed = !string.IsNullOrWhiteSpace(confirmedPath) &&
                    string.Equals(confirmedPath, outputPath, StringComparison.OrdinalIgnoreCase);
                if (!saveOk || saveErrors != 0 || !fileExists || !pathConfirmed)
                    throw new Fault("SAVE_FAILED", "SOLIDWORKS save failed. api_success=" + saveOk +
                        ", errors=" + saveErrors + ", warnings=" + saveWarnings + ", file_exists=" + fileExists +
                        ", confirmed_path=" + (confirmedPath ?? "<empty>") + ", requested_path=" + outputPath);
                saved = true;

                bool previousUnchanged = true;
                if (previous != null)
                    previousUnchanged = Text(Call(previous, "IModelDoc2", "GetTitle")) == previousTitle &&
                        Text(Call(previous, "IModelDoc2", "GetPathName")) == previousPath &&
                        Bool(Call(previous, "IModelDoc2", "GetSaveFlag")) == previousDirty;

                return Json.Obj("operation", "CREATED_NEW_TURNED_PART", "connector_version", Program.Version,
                    "file_path", outputPath, "document_left_open", true, "material_assigned", false,
                    "plan", plan.ToJson(), "template", Json.Obj("path", template, "source", templateSource),
                    "features", Json.Obj("revolve", true, "blind_axial_bore", plan.Bore.Count > 0,
                        "radial_hole_count", plan.RadialHoles.Count, "side_flat_slot_count", plan.SideSlots.Count,
                        "longitudinal_spline_count", plan.Spline == null ? 0 : plan.Spline.ToothCount,
                        "properties_written", writtenProperties),
                    "save", Json.Obj("method", "IModelDocExtension.SaveAs3", "api_success", saveOk,
                        "errors", saveErrors, "warnings", saveWarnings, "path_confirmed", pathConfirmed),
                    "verification", Json.Obj("status", "PASS", "method", "IMassProperty.Volume",
                        "axisymmetric_expected_volume_m3", plan.AxisymmetricVolumeM3,
                        "axisymmetric_actual_volume_m3", revolvedVolume, "axisymmetric_relative_error", revolvedError,
                        "after_spline_volume_m3", splineVolume,
                        "final_volume_m3", finalVolume, "reference_volume_m3", plan.ReferenceVolumeM3,
                        "reference_relative_error", referenceError, "approximate_bbox_xyz_mm", ApproximateBox(created)),
                    "existing_document", Json.Obj("title", previousTitle, "path", previousPath, "unchanged", previousUnchanged),
                    "supported_scope", "Turned Plan v2 remains supported. Plan v3 adds one straight external longitudinal-spline zone, an axial spline-end taper, and optional designation/name properties. Profile fillets are represented by validated profile points. No threads, arbitrary edge selection or material assignment.",
                    "safety", "A new uniquely named SLDPRT was created from validated numeric data. Existing documents were not saved, rebuilt, closed or edited. Human review is required.",
                    "manufacturing_approved", false);
            }
            catch
            {
                if (!saved && created != null && !string.IsNullOrEmpty(createdTitle))
                {
                    try { Call(app, "ISldWorks", "CloseDoc", createdTitle); } catch { }
                }
                throw;
            }
        }
        object BeginCutSketchOnPlane(object target, int planeIndex)
        {
            object plane = ReferencePlane(target, planeIndex);
            if (!Convert.ToBoolean(Call(plane, "IFeature", "Select2", false, 0)))
                throw new Fault("SKETCH_PLANE_NOT_FOUND", "Cannot select reference plane index " + planeIndex + " for a validated profile hole.");
            object sketch = Get(target, "IModelDoc2", "SketchManager");
            Call(sketch, "ISketchManager", "InsertSketch", true);
            return sketch;
        }

        void CreateProfileHoleCut(object target, int planeIndex, ProfileHole hole, double thicknessMm,
            bool throughBothWalls, string label)
        {
            object sketch = BeginCutSketchOnPlane(target, planeIndex);
            // Axis mapping confirmed empirically against a live SOLIDWORKS 2026
            // session (control plan AI_CONTROL_PROFILE_ANGLE_01, verified again
            // against the real-drawing plan 05.SHT.TR.11.00.00.05): the base
            // cross section (reference-plane index 0) sketches its local (x,y)
            // directly onto global (X,Y), extruding along global Z as the part's
            // length axis. Reference-plane index 1 (coincident with leg_a's outer
            // face, global Y=0) maps its own local (x,y) to global (X,-Z): local x is
            // the edge-offset axis directly, local y is the NEGATIVE of the length
            // axis. Reference-plane index 2 (leg_b's outer face, global X=0) maps
            // local (x,y) to global (-Z,Y): local x is the negative length axis,
            // local y is the edge-offset axis directly. Both planes carry length as
            // one in-plane axis as expected, each with a sign flip, but on a
            // DIFFERENT one of their own two local axes -- not simple swapped copies
            // of each other. Feeding (axial, edge_offset) unswapped and unnegated, as
            // a first guess would, places the circle at length position -axial,
            // beyond the far end of the body (which spans 0..LengthMm), and the cut
            // silently finds no material to cut through.
            double localX, localY;
            if (planeIndex == 1) { localX = hole.EdgeOffsetMm / 1000.0; localY = -hole.AxialMm / 1000.0; }
            else { localX = -hole.AxialMm / 1000.0; localY = hole.EdgeOffsetMm / 1000.0; }
            if (Call(sketch, "ISketchManager", "CreateCircleByRadius", localX, localY, 0.0, hole.Radius / 1000.0) == null)
                throw new Fault("SKETCH_FAILED", "Cannot sketch " + label + ".");
            // Blind cut bounded by the plan's own validated leg thickness, rather
            // than ThroughAll. Discovered live against a 4000mm-long real drawing
            // plan: ThroughAll on a reference plane coincident with a leg's outer
            // face -- which must ray-cast through the ENTIRE length of a very
            // long, thin, sharp-cornered extrusion to find where material ends --
            // unexpectedly split the single solid body into two separate bodies
            // on the very first hole cut. A Blind cut of exactly the validated leg
            // thickness is geometrically unambiguous regardless of the part's
            // overall length and needs no ray-casting through the far end of the
            // body. allowDirectionFallback handles the remaining ambiguity of
            // which side of the reference plane the material sits on.
            // An angle hole removes one leg wall. A rectangular-tube hole is
            // explicitly defined as a coaxial cut through both opposite walls.
            // This distinction is part of Plan v2 and of the analytic volume.
            FinishCutSketch(target, sketch, throughBothWalls, thicknessMm, label,
                allowDirectionFallback: true);
            // Permanent safety check: verify every single hole cut leaves exactly
            // one solid body. If a future plan combination ever reintroduces a
            // body-splitting cut, this fails fast with a clear, specific error
            // immediately on the offending hole instead of surfacing many holes
            // later as an opaque SKETCH_FAILED, and prevents ever saving a part
            // with a silently-corrupted body count.
            VerifySingleProfileBody(target, label);
        }

        void VerifySingleProfileBody(object target, string label)
        {
            int solidBodyType = EnumValue("swBodyType_e", "swSolidBody");
            var bodiesAfterCut = Call(target, "IPartDoc", "GetBodies2", solidBodyType, false) as Array;
            int bodyCountAfterCut = bodiesAfterCut == null ? 0 : bodiesAfterCut.Length;
            if (bodyCountAfterCut != 1)
                throw new Fault("CUT_SPLIT_BODY", "SOLIDWORKS reported " + bodyCountAfterCut +
                    " solid bodies after cutting " + label + " (expected exactly 1). The file was not saved.");
        }

        double[] ProfileSketchPoint(int planeIndex, double axialMm, double edgeOffsetMm)
        {
            if (planeIndex == 1)
                return new[] { edgeOffsetMm, -axialMm };
            return new[] { -axialMm, edgeOffsetMm };
        }

        void CreateProfileSlotCut(object target, int planeIndex, ProfileSlot slot,
            double thicknessMm, bool throughBothWalls, string label)
        {
            double axial1 = slot.AxialMm - slot.StraightLength / 2.0;
            double axial2 = slot.AxialMm + slot.StraightLength / 2.0;
            double edge1 = slot.EdgeOffsetMm - slot.Radius;
            double edge2 = slot.EdgeOffsetMm + slot.Radius;

            object rectangleSketch = BeginCutSketchOnPlane(target, planeIndex);
            var rectangle = new List<double[]> {
                ProfileSketchPoint(planeIndex, axial1, edge1),
                ProfileSketchPoint(planeIndex, axial2, edge1),
                ProfileSketchPoint(planeIndex, axial2, edge2),
                ProfileSketchPoint(planeIndex, axial1, edge2)
            };
            SketchClosedPolygon(rectangleSketch, rectangle, label + " centre rectangle");
            FinishCutSketch(target, rectangleSketch, throughBothWalls, thicknessMm,
                label + " centre rectangle", allowDirectionFallback: true);
            VerifySingleProfileBody(target, label + " centre rectangle");

            object capSketch = BeginCutSketchOnPlane(target, planeIndex);
            foreach (double axial in new[] { axial1, axial2 })
            {
                double[] p = ProfileSketchPoint(planeIndex, axial, slot.EdgeOffsetMm);
                if (Call(capSketch, "ISketchManager", "CreateCircleByRadius",
                    p[0] / 1000.0, p[1] / 1000.0, 0.0,
                    slot.Radius / 1000.0) == null)
                    throw new Fault("SKETCH_FAILED", "Cannot sketch both circular caps of " + label + ".");
            }
            FinishCutSketch(target, capSketch, throughBothWalls, thicknessMm,
                label + " circular caps", allowDirectionFallback: true);
            VerifySingleProfileBody(target, label + " circular caps");
        }

        void SketchRoundedRectangleLoop(object target, object sketch, double leftMm, double bottomMm,
            double widthMm, double heightMm, double radiusMm, string label)
        {
            double rightMm = leftMm + widthMm, topMm = bottomMm + heightMm;
            if (radiusMm <= 0.0)
            {
                SketchClosedPolygon(sketch, new List<double[]> {
                    new[] { leftMm, bottomMm }, new[] { rightMm, bottomMm },
                    new[] { rightMm, topMm }, new[] { leftMm, topMm }
                }, label);
                return;
            }

            // Let SOLIDWORKS own both contour connectivity and corner trimming. Creating
            // independent lines and arcs at numerically coincident coordinates produced
            // template-dependent open/complementary contours. A corner rectangle shares
            // real sketch points; CreateFillet then trims its adjacent lines and creates
            // the exact tangent arc without our choosing an arc direction.
            Array rectangle = Call(sketch, "ISketchManager", "CreateCornerRectangle",
                leftMm / 1000.0, bottomMm / 1000.0, 0.0,
                rightMm / 1000.0, topMm / 1000.0, 0.0) as Array;
            if (rectangle == null || rectangle.Length != 4)
                throw new Fault("SKETCH_FAILED", "Cannot create the connected base rectangle of " + label + ".");

            double[,] corners = {
                { leftMm, bottomMm }, { rightMm, bottomMm },
                { rightMm, topMm }, { leftMm, topMm }
            };
            for (int i = 0; i < 4; i++)
            {
                Call(target, "IModelDoc2", "ClearSelection2", true);
                object corner = FindRectangleCorner(rectangle,
                    corners[i, 0] / 1000.0, corners[i, 1] / 1000.0);
                if (!Convert.ToBoolean(Call(corner, "ISketchPoint", "Select4", false, null)))
                    throw new Fault("SKETCH_FAILED", "Cannot select corner " + (i + 1) + " of " + label + ".");
                object fillet = Call(sketch, "ISketchManager", "CreateFillet",
                    radiusMm / 1000.0,
                    EnumValue("swConstrainedCornerAction_e", "swConstrainedCornerDeleteGeometry"));
                if (fillet == null)
                    throw new Fault("SKETCH_FAILED", "Cannot create corner fillet " + (i + 1) + " of " + label + ".");
            }
            Call(target, "IModelDoc2", "ClearSelection2", true);
        }

        void SketchProfileCrossSection(object target, object sketch, ProfilePartPlan plan)
        {
            if (plan.IsEqualAngle)
            {
                var points = new List<double[]>();
                foreach (double[] p in plan.CrossSectionPolygonYZ()) points.Add(new[] { p[0], p[1] });
                SketchClosedPolygon(sketch, points, "the equal-angle cross-section");
                return;
            }
            if (plan.IsRectangularTube)
            {
                SketchRoundedRectangleLoop(target, sketch, 0.0, 0.0, plan.WidthMm, plan.HeightMm,
                    plan.OuterCornerRadiusMm, "the rectangular-tube outer contour");
                SketchRoundedRectangleLoop(target, sketch, plan.ThicknessMm, plan.ThicknessMm,
                    plan.WidthMm - 2.0 * plan.ThicknessMm,
                    plan.HeightMm - 2.0 * plan.ThicknessMm,
                    plan.InnerCornerRadiusMm, "the rectangular-tube inner contour");
                return;
            }

            if (Call(sketch, "ISketchManager", "CreateCircleByRadius", 0.0, 0.0, 0.0,
                plan.OuterDiameterMm / 2000.0) == null ||
                Call(sketch, "ISketchManager", "CreateCircleByRadius", 0.0, 0.0, 0.0,
                plan.InnerDiameterMm / 2000.0) == null)
                throw new Fault("SKETCH_FAILED", "Cannot create both concentric circles of the round-tube cross-section.");
        }

        object ApplyProfilePartCreationProperties(object target, ProfilePartPlan plan)
        {
            var configurationManager = Get(target, "IModelDoc2", "ConfigurationManager");
            var activeConfiguration = Get(configurationManager, "IConfigurationManager", "ActiveConfiguration");
            string configurationName = Text(Get(activeConfiguration, "IConfiguration", "Name"));
            var extension = Get(target, "IModelDoc2", "Extension");
            var manager = Get(extension, "IModelDocExtension", "CustomPropertyManager", configurationName);
            int textType = EnumValue("swCustomInfoType_e", "swCustomInfoText");
            int replace = EnumValue("swCustomPropertyAddOption_e", "swCustomPropertyDeleteAndAdd");
            var written = new List<object>();
            if (plan.Properties != null)
            {
                if (plan.Properties.Designation != null)
                    written.Add(WriteAndVerifyProperty(manager, "Обозначение", plan.Properties.Designation, textType, replace));
                if (plan.Properties.Name != null)
                    written.Add(WriteAndVerifyProperty(manager, "Наименование", plan.Properties.Name, textType, replace));
            }
            written.Add(WriteAndVerifyProperty(manager, "AI_Тип_профиля", plan.ProfileTypeId, textType, replace));
            written.Add(WriteAndVerifyProperty(manager, "AI_Длина_мм", plan.LengthMm.ToString("G17", CultureInfo.InvariantCulture), textType, replace));
            written.Add(WriteAndVerifyProperty(manager, "AI_Толщина_мм", plan.ThicknessMm.ToString("G17", CultureInfo.InvariantCulture), textType, replace));
            if (plan.IsEqualAngle)
            {
                written.Add(WriteAndVerifyProperty(manager, "AI_Полка_A_мм", plan.LegAMm.ToString("G17", CultureInfo.InvariantCulture), textType, replace));
                written.Add(WriteAndVerifyProperty(manager, "AI_Полка_B_мм", plan.LegBMm.ToString("G17", CultureInfo.InvariantCulture), textType, replace));
            }
            else if (plan.IsRectangularTube)
            {
                written.Add(WriteAndVerifyProperty(manager, "AI_Ширина_мм", plan.WidthMm.ToString("G17", CultureInfo.InvariantCulture), textType, replace));
                written.Add(WriteAndVerifyProperty(manager, "AI_Высота_мм", plan.HeightMm.ToString("G17", CultureInfo.InvariantCulture), textType, replace));
                written.Add(WriteAndVerifyProperty(manager, "AI_Наружный_R_мм", plan.OuterCornerRadiusMm.ToString("G17", CultureInfo.InvariantCulture), textType, replace));
                written.Add(WriteAndVerifyProperty(manager, "AI_Внутренний_R_мм", plan.InnerCornerRadiusMm.ToString("G17", CultureInfo.InvariantCulture), textType, replace));
            }
            else
            {
                written.Add(WriteAndVerifyProperty(manager, "AI_Наружный_D_мм", plan.OuterDiameterMm.ToString("G17", CultureInfo.InvariantCulture), textType, replace));
                written.Add(WriteAndVerifyProperty(manager, "AI_Внутренний_D_мм", plan.InnerDiameterMm.ToString("G17", CultureInfo.InvariantCulture), textType, replace));
            }
            written.Add(WriteAndVerifyProperty(manager, "AI_Отверстий_всего", plan.Holes.Count.ToString(CultureInfo.InvariantCulture), textType, replace));
            written.Add(WriteAndVerifyProperty(manager, "AI_Пазов_всего", plan.Slots.Count.ToString(CultureInfo.InvariantCulture), textType, replace));
            return Json.Obj("configuration", configurationName, "items", written.ToArray(),
                "note", "Audited numeric profile-plan data; manufacturing approval still requires human review.");
        }

        object CreateProfilePartFromPlan(Dictionary<string, object> args)
        {
            ProfilePartPlan plan = ProfilePartPlan.Parse(args);

            object previous = Get(app, "ISldWorks", "IActiveDoc2");
            string previousTitle = previous == null ? null : Text(Call(previous, "IModelDoc2", "GetTitle"));
            string previousPath = previous == null ? null : Text(Call(previous, "IModelDoc2", "GetPathName"));
            bool? previousDirty = previous == null ? null : Bool(Call(previous, "IModelDoc2", "GetSaveFlag"));

            string templateSource;
            string template = FindPartTemplate(out templateSource);
            object created = null; string createdTitle = null; bool saved = false;
            try
            {
                created = Call(app, "ISldWorks", "NewDocument", template, 0, 0.0, 0.0);
                if (created == null) throw new Fault("CREATE_DOCUMENT_FAILED", "SOLIDWORKS did not create a new part document.");
                createdTitle = Text(Call(created, "IModelDoc2", "GetTitle"));
                if (Convert.ToInt32(Call(created, "IModelDoc2", "GetType")) != 1)
                    throw new Fault("WRONG_TEMPLATE_TYPE", "The configured default template did not create a part document.");

                object plane = FirstReferencePlane(created);
                if (!Convert.ToBoolean(Call(plane, "IFeature", "Select2", false, 0)))
                    throw new Fault("SKETCH_PLANE_NOT_FOUND", "Cannot select the first reference plane for the profile cross-section.");
                var sketch = Get(created, "IModelDoc2", "SketchManager");
                Call(sketch, "ISketchManager", "InsertSketch", true);

                SketchProfileCrossSection(created, sketch, plan);
                Call(sketch, "ISketchManager", "InsertSketch", true);

                var features = Get(created, "IModelDoc2", "FeatureManager");
                object extrusion = Call(features, "IFeatureManager", "FeatureExtrusion2",
                    true, false, false, 0, 0, plan.LengthMm / 1000.0, plan.LengthMm / 1000.0,
                    false, false, false, false, 0.0, 0.0, false, false, false, false,
                    true, true, true, 0, 0.0, false);
                if (extrusion == null) throw new Fault("EXTRUSION_FAILED", "SOLIDWORKS did not create the profile extrusion.");
                Call(created, "IModelDoc2", "EditRebuild3");

                double baseVolume = VolumeOf(created);
                double baseExpectedM3 = plan.CrossSectionAreaMm2 * plan.LengthMm * 1e-9;
                double baseError = Math.Abs(baseVolume - baseExpectedM3) / baseExpectedM3;
                if (baseError > 0.001)
                    throw new Fault("GEOMETRY_VERIFICATION_FAILED",
                        "The base extrusion volume differs from the validated cross-section by more than 0.1%. " +
                        "expected_volume_m3=" + baseExpectedM3.ToString("G17", CultureInfo.InvariantCulture) +
                        ", actual_volume_m3=" + baseVolume.ToString("G17", CultureInfo.InvariantCulture) +
                        ", expected_area_mm2=" + plan.CrossSectionAreaMm2.ToString("G17", CultureInfo.InvariantCulture) +
                        ", actual_area_mm2=" + (baseVolume * 1e9 / plan.LengthMm).ToString("G17", CultureInfo.InvariantCulture) +
                        ", relative_error=" + baseError.ToString("G17", CultureInfo.InvariantCulture) +
                        ". The file was not saved.");

                foreach (ProfileHole hole in plan.Holes)
                {
                    int planeIndex = hole.Face == "leg_a" || hole.Face == "face_a" ? 1 : 2;
                    CreateProfileHoleCut(created, planeIndex, hole, plan.ThicknessMm,
                        plan.IsRectangularTube, "a validated hole on " + hole.Face);
                }
                foreach (ProfileSlot slot in plan.Slots)
                {
                    int planeIndex = slot.Face == "leg_a" || slot.Face == "face_a" ? 1 : 2;
                    CreateProfileSlotCut(created, planeIndex, slot, plan.ThicknessMm,
                        plan.IsRectangularTube, "a validated axial slot on " + slot.Face);
                }

                double finalVolume = VolumeOf(created);
                double finalError = Math.Abs(finalVolume - plan.ExpectedVolumeM3) / plan.ExpectedVolumeM3;
                if (finalError > 0.001)
                    throw new Fault("GEOMETRY_VERIFICATION_FAILED", "The final volume differs from the validated plan by more than 0.1%. The file was not saved.");

                var holeRadiiMm = new List<double>();
                foreach (ProfileHole hole in plan.Holes)
                    for (int wall = 0; wall < hole.WallCount; wall++) holeRadiiMm.Add(hole.Radius);
                foreach (ProfileSlot slot in plan.Slots)
                    for (int wall = 0; wall < slot.WallCount; wall++)
                        for (int cap = 0; cap < 2; cap++) holeRadiiMm.Add(slot.Radius);
                var sectionCutRadiiMm = new List<double>();
                double? sectionOuterRadiusMm = null;
                var sectionCornerRadiiMm = new List<double>();
                if (plan.IsRoundTube)
                {
                    sectionOuterRadiusMm = plan.OuterDiameterMm / 2.0;
                    sectionCutRadiiMm.Add(plan.InnerDiameterMm / 2.0);
                }
                if (plan.IsRectangularTube && plan.OuterCornerRadiusMm > 0.0)
                {
                    for (int corner = 0; corner < 4; corner++)
                    {
                        sectionCornerRadiiMm.Add(plan.OuterCornerRadiusMm);
                        if (plan.InnerCornerRadiusMm > 0.0)
                            sectionCornerRadiiMm.Add(plan.InnerCornerRadiusMm);
                    }
                }
                object topology = VerifyPrismaticCylinders(created, sectionOuterRadiusMm, holeRadiiMm,
                    sectionCutRadiiMm, null, sectionCornerRadiiMm);

                object writtenProperties = ApplyProfilePartCreationProperties(created, plan);
                object materialInfo = ApplyAndVerifyMaterial(created, plan.MaterialName);

                string outputDir = Program.EnsureWorkspace();
                string outputPath = Path.Combine(outputDir, "AI_PROFILE_PART_" + DateTime.UtcNow.ToString("yyyyMMdd_HHmmss") +
                    "_" + Guid.NewGuid().ToString("N").Substring(0, 8) + ".SLDPRT");
                var saveExtension = Get(created, "IModelDoc2", "Extension");
                object[] saveArgs = { outputPath, 0, 1, null, null, 0, 0 };
                bool saveOk = Convert.ToBoolean(Call(saveExtension, "IModelDocExtension", "SaveAs3", saveArgs));
                int saveErrors = Convert.ToInt32(saveArgs[5], CultureInfo.InvariantCulture);
                int saveWarnings = Convert.ToInt32(saveArgs[6], CultureInfo.InvariantCulture);
                bool fileExists = File.Exists(outputPath);
                string confirmedPath = Text(Call(created, "IModelDoc2", "GetPathName"));
                bool pathConfirmed = !string.IsNullOrWhiteSpace(confirmedPath) &&
                    string.Equals(confirmedPath, outputPath, StringComparison.OrdinalIgnoreCase);
                if (!saveOk || saveErrors != 0 || !fileExists || !pathConfirmed)
                    throw new Fault("SAVE_FAILED", "SOLIDWORKS save failed. api_success=" + saveOk +
                        ", errors=" + saveErrors + ", warnings=" + saveWarnings + ", file_exists=" + fileExists +
                        ", confirmed_path=" + (confirmedPath ?? "<empty>") + ", requested_path=" + outputPath);
                saved = true;

                bool previousUnchanged = true;
                if (previous != null)
                    previousUnchanged = Text(Call(previous, "IModelDoc2", "GetTitle")) == previousTitle &&
                        Text(Call(previous, "IModelDoc2", "GetPathName")) == previousPath &&
                        Bool(Call(previous, "IModelDoc2", "GetSaveFlag")) == previousDirty;

                return Json.Obj("operation", "CREATED_NEW_PROFILE_PART", "connector_version", Program.Version,
                    "file_path", outputPath, "document_left_open", true,
                    "plan", plan.ToJson(), "template", Json.Obj("path", template, "source", templateSource),
                    "written_properties", writtenProperties,
                    "material", materialInfo,
                    "save", Json.Obj("method", "IModelDocExtension.SaveAs3", "api_success", saveOk,
                        "errors", saveErrors, "warnings", saveWarnings, "path_confirmed", pathConfirmed),
                    "verification", Json.Obj("status", "PASS", "expected_volume_m3", plan.ExpectedVolumeM3,
                        "actual_volume_m3", finalVolume, "relative_error", finalError,
                        "topology", topology),
                    "existing_document", Json.Obj("title", previousTitle, "path", previousPath, "unchanged", previousUnchanged),
                    "supported_scope", "Profile Plan v1/v2/v3: equal-angle, rectangular tube (sharp or explicitly dimensioned constant-wall corner radii) and round tube. Both ends are plain perpendicular cuts. Equal-angle holes/axial obround slots cut one leg; rectangular-tube face_a/face_b cuts pass through both opposite walls. Hole and slot positions may be explicit or a uniform linear pattern. Slots require Plan v3. Round-tube side cuts, mitred/angled ends, end chamfers, channel/I-beam, countersinks, bends and threads are not supported.",
                    "safety", "A new uniquely named SLDPRT was created in local Workspace. Existing documents were not saved, rebuilt, closed or edited. Cross-section, volume, solid-body count and cylindrical topology were checked against the numeric plan. Human review is still required before manufacturing.",
                    "manufacturing_approved", false);
            }
            catch
            {
                if (!saved && created != null && !string.IsNullOrEmpty(createdTitle))
                {
                    try { Call(app, "ISldWorks", "CloseDoc", createdTitle); } catch { }
                }
                throw;
            }
        }

        void CheckUnchanged()
        {
            var current = Get(app, "ISldWorks", "IActiveDoc2");
            if (current == null || !Object.ReferenceEquals(current, model))
                throw new Fault("DOCUMENT_CHANGED", "Активный документ изменился во время чтения. Повторите запрос, не переключая модель.");
            if (Text(Call(model, "IModelDoc2", "GetPathName")) != path || Text(Call(model, "IModelDoc2", "GetTitle")) != title ||
                Bool(Call(model, "IModelDoc2", "GetSaveFlag")) != dirty)
                throw new Fault("DOCUMENT_CHANGED", "Документ изменился во время чтения. Повторите запрос без редактирования модели.");
            if (kind == 1 || kind == 2)
            {
                var mgr = Get(model, "IModelDoc2", "ConfigurationManager");
                var cfg = Get(mgr, "IConfigurationManager", "ActiveConfiguration");
                if (Text(Get(cfg, "IConfiguration", "Name")) != config) throw new Fault("CONFIGURATION_CHANGED", "Active configuration changed.");
            }
        }
        object Execute(string tool, Dictionary<string, object> args)
        {
            Connect();
            if (tool == "sw_test_pack_and_go") return TestPackAndGo(args);
            if (tool == "sw_test_document") return TestDocument(args);
            if (tool == "sw_status") return Json.Obj("connected", true, "connector_version", Program.Version, "solidworks_api_revision", revision,
                "interop_path", interopPath, "interop_assembly", interop.FullName, "sta", System.Threading.Thread.CurrentThread.GetApartmentState().ToString(),
                "writes_to_model", true, "workspace_path", Program.EnsureWorkspace(), "local_only", true,
                "storage_policy", Json.Obj("allowed_write_drive_type", "Fixed",
                    "allowed_document_types", new[] { "SLDPRT", "SLDDRW" },
                    "blocked", new[] { "UNC", "mapped_network_drive", "removable_drive", "optical_drive", "ram_drive", "symbolic_link", "junction", "assembly", "PDM_write" },
                    "existing_file_backup", "UNIQUE_VERIFIED_SIBLING"),
                "experiment_policy", Json.Obj("tools", new[] { "sw_test_pack_and_go", "sw_test_document" },
                    "opt_in_required", "TestScope.local.json plus explicit user authorization",
                    "write_scope", "Registered test folder and complete local dependency closure only",
                    "capabilities", "Pack and Go copies; guarded audit, rebuild/save and clean close/reopen of test parts and assemblies",
                    "other_open_documents", "Protected file hashes, dirty states and configurations"),
                "write_tools_available", new[] { "sw_copy_active_to_workspace", "sw_save_workspace_document", "sw_set_workspace_properties", "sw_set_parameter", "sw_set_parameters", "sw_set_feature_dimensions", "sw_set_global_variable", "sw_create_parameter_variant", "sw_create_plate", "sw_create_part_from_plan", "sw_create_sheet_from_contours", "sw_create_turned_part_from_plan", "sw_create_profile_part_from_plan", "sw_create_drawing", "sw_export_workspace_pdf" },
                "read_tools_available", new[] { "sw_document", "sw_properties", "sw_part", "sw_parameters", "sw_features", "sw_components", "sw_drawing", "sw_export_snapshot", "sw_open_assembly_readonly", "sw_assembly_tree", "sw_equations", "sw_configurations", "sw_document_dependencies", "sw_component_details" },
                "write_policy", "Existing active SLDPRT and SLDDRW files may be changed only when their resolved existing path is on a ready local fixed disk. UNC paths, mapped network drives, removable drives, symbolic links and junctions are blocked. In-place writes create a verified unique sibling backup. sw_set_feature_dimensions accepts only exact directly owned verified linear driving dimensions of one non-suppressed Extrusion, Boss, Cut, HoleWzd, Chamfer or Fillet returned by sw_features. sw_set_global_variable accepts the same dimensions and additionally requires a new, not-already-used ASCII variable_name; it adds exactly two IEquationMgr equations (the named global variable and the dimension now referencing it) and deletes both plus restores the literal value on any verification failure. New part creation remains in Workspace; local variants, drawings and PDFs receive unique sibling names. Ordinary tools do not write assemblies; the only exception is the separately opted-in experiment_policy. PDM actions, macros, shell commands and arbitrary COM calls are not accepted. Assembly read tools and dependency inventories do not grant write authorization.",
                "computer", Environment.MachineName);
            if (tool == "sw_workspace_status") return WorkspaceStatus(args);
            if (tool == "sw_copy_active_to_workspace") return CopyActiveToWorkspace();
            if (tool == "sw_open_workspace_file") return OpenWorkspaceFile(args);
            if (tool == "sw_open_local_file") return OpenLocalFile(args);
            if (tool == "sw_open_assembly_readonly") return OpenAssemblyReadOnly(args);
            if (tool == "sw_document_dependencies") return DocumentDependencies(args);
            if (tool == "sw_save_workspace_document") return SaveWorkspaceDocument();
            if (tool == "sw_set_workspace_properties") return SetWorkspaceProperties(args);
            if (tool == "sw_set_parameter") return SetWorkspaceParameter(args);
            if (tool == "sw_set_parameters") return SetWorkspaceParameters(args);
            if (tool == "sw_set_feature_dimensions") return SetFeatureDimensions(args);
            if (tool == "sw_set_global_variable") return SetGlobalVariable(args);
            if (tool == "sw_create_parameter_variant") return CreateParameterVariant(args);
            if (tool == "sw_create_plate") return CreatePlate(args);
            if (tool == "sw_create_part_from_plan") return CreatePartFromPlan(args);
            if (tool == "sw_create_sheet_from_contours") return CreateSheetFromContours(args);
            if (tool == "sw_create_turned_part_from_plan") return CreateTurnedPartFromPlan(args);
            if (tool == "sw_create_profile_part_from_plan") return CreateProfilePartFromPlan(args);
            if (tool == "sw_create_drawing") return CreateDrawing(args);
            if (tool == "sw_export_workspace_pdf") return ExportWorkspacePdf();
            Document();
            object data;
            switch (tool)
            {
                case "sw_document": data = DocumentData(); break;
                case "sw_properties": data = AllProperties(); break;
                case "sw_part": data = PartData(); break;
                case "sw_parameters": data = ParametersData(); break;
                case "sw_features": data = FeaturesData(args); break;
                case "sw_components": data = Components(args); break;
                case "sw_assembly_tree": data = AssemblyTree(args); break;
                case "sw_component_details": data = ComponentDetails(args); break;
                case "sw_equations": data = EquationsData(); break;
                case "sw_configurations": data = ConfigurationsData(); break;
                case "sw_drawing": data = DrawingData(); break;
                case "sw_export_snapshot":
                    data = Json.Obj("document", DocumentData(), "properties", AllProperties(),
                        "part", kind == 1 ? PartData() : null,
                        "assembly", kind == 2 ? Components(Json.Obj("limit", 50)) : null,
                        "drawing", kind == 3 ? DrawingData() : null); break;
                default: throw new Fault("UNKNOWN_TOOL", tool);
            }
            CheckUnchanged();
            return Json.Obj("schema_version", "solidworks-local/1.3", "context", Context(), "data", data, "issues", issues,
                "partial", issues.Count > 0, "manufacturing_approved", false,
                "consistency", "Best-effort live read, not a locked transaction. Do not edit the document during extraction.",
                "untrusted_text", true);
        }
    }
}
