using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;

namespace SolidWorksLocal
{
    // Explicit opt-in experiment commands; ordinary assembly write guards remain unchanged.
    internal sealed partial class SolidWorksReader
    {
        internal static bool TestPathInside(string root, string candidate)
        {
            if (string.IsNullOrWhiteSpace(root) || string.IsNullOrWhiteSpace(candidate) ||
                Program.IsNetworkOrDevicePathText(root) || Program.IsNetworkOrDevicePathText(candidate) ||
                !Path.IsPathRooted(root) || !Path.IsPathRooted(candidate)) return false;
            string fullRoot = Path.GetFullPath(root).TrimEnd(Path.DirectorySeparatorChar, Path.AltDirectorySeparatorChar);
            if (fullRoot.Length <= Path.GetPathRoot(fullRoot).TrimEnd('\\', '/').Length) return false;
            return Path.GetFullPath(candidate).StartsWith(fullRoot + Path.DirectorySeparatorChar, StringComparison.OrdinalIgnoreCase);
        }

        string TestRoot(Dictionary<string, object> args)
        {
            string policy = Path.Combine(Program.Root, "TestScope.local.json");
            if (!File.Exists(policy)) throw new Fault("TEST_SCOPE_NOT_CONFIGURED", "Configure the explicitly authorized test_root in TestScope.local.json beside this EXE first.");
            Program.RequireLocalFixedPath(policy, true);
            var settings = Json.Map(Json.Decode(File.ReadAllText(policy, Program.Utf8)));
            string configured = Catalog.TextValue(settings, "test_root", true, 2048);
            string requested = Catalog.TextValue(args, "test_root", true, 2048);
            string root = Path.GetFullPath(configured).TrimEnd('\\', '/');
            if (!string.Equals(root, Path.GetFullPath(requested).TrimEnd('\\', '/'), StringComparison.OrdinalIgnoreCase) ||
                !TestPathInside(root, Path.Combine(root, "scope-probe.SLDPRT")) || !Directory.Exists(root))
                throw new Fault("TEST_SCOPE_MISMATCH", "Requested test_root differs from the configured experiment folder or is too broad.");
            Program.RequireLocalFixedPath(Path.Combine(root, "scope-probe.SLDPRT"), false);
            return root;
        }

        string TestFile(string root, string candidate)
        {
            if (!TestPathInside(root, candidate)) throw new Fault("TEST_SCOPE_ESCAPE", "File is outside the registered test folder: " + candidate);
            string value = Program.RequireLocalFixedPath(candidate, true);
            string ext = Path.GetExtension(value);
            if (!ext.Equals(".SLDPRT", StringComparison.OrdinalIgnoreCase) && !ext.Equals(".SLDASM", StringComparison.OrdinalIgnoreCase))
                throw new Fault("TEST_DOCUMENT_TYPE", "Only test SLDPRT and SLDASM files are supported.");
            return value;
        }

        List<string> TestDependencies(string file)
        {
            var raw = Call(app, "ISldWorks", "GetDocumentDependencies2", file, false, false, false) as Array;
            int count = Convert.ToInt32(Call(app, "ISldWorks", "GetDocumentDependenciesCount", file, 0, 0));
            if (raw == null || raw.Length == 0)
            {
                if (count != 0) throw new Fault("TEST_DEPENDENCIES_UNKNOWN", "Dependency count and list disagree for " + file);
                return new List<string>();
            }
            if (raw.Length % 2 != 0) throw new Fault("TEST_DEPENDENCIES_UNKNOWN", "Expected complete name/path dependency pairs.");
            var result = new List<string>();
            for (int i = 1; i < raw.Length; i += 2)
            {
                string dependency = Text(raw.GetValue(i));
                if (string.IsNullOrWhiteSpace(dependency) || !Path.IsPathRooted(dependency))
                    throw new Fault("TEST_DEPENDENCIES_UNKNOWN", "Unresolved dependency in " + file);
                result.Add(Path.GetFullPath(dependency));
            }
            return result;
        }

        HashSet<string> TestClosure(string root, string file)
        {
            var result = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
            var pending = new Queue<string>(); pending.Enqueue(file);
            while (pending.Count > 0)
            {
                string next = TestFile(root, pending.Dequeue());
                if (!result.Add(next)) continue;
                if (result.Count > 250) throw new Fault("TEST_SCOPE_TOO_LARGE", "At most 250 unique files per experiment operation.");
                foreach (string dep in TestDependencies(next)) pending.Enqueue(dep);
            }
            return result;
        }

        Array TestOpenDocuments()
        {
            var documents = Call(app, "ISldWorks", "GetDocuments") as Array;
            int count = Convert.ToInt32(Call(app, "ISldWorks", "GetDocumentCount"));
            if ((documents == null ? 0 : documents.Length) != count)
                throw new Fault("TEST_DOCUMENT_LIST_UNKNOWN", "Cannot establish all other loaded documents.");
            return documents ?? new object[0];
        }

        List<object[]> TestProtectDocuments(HashSet<string> allowed)
        {
            var result = new List<object[]>();
            foreach (object doc in TestOpenDocuments())
            {
                string docPath = Text(Call(doc, "IModelDoc2", "GetPathName"));
                if (!string.IsNullOrEmpty(docPath) && allowed.Contains(docPath)) continue;
                object state = Call(doc, "IModelDoc2", "GetSaveFlag");
                if (state == null) throw new Fault("TEST_DOCUMENT_STATE_UNKNOWN", "Cannot protect an unrelated document with unknown dirty state.");
                result.Add(new object[] { doc, docPath, state, TestConfiguration(doc),
                    string.IsNullOrEmpty(docPath) ? null : FileSha256(docPath) });
            }
            return result;
        }

        void TestVerifyProtected(List<object[]> protectedDocs)
        {
            var current = new List<object>(); foreach (object doc in TestOpenDocuments()) current.Add(doc);
            foreach (object[] entry in protectedDocs)
            {
                object doc = entry[0]; string file = (string)entry[1];
                if (!current.Contains(doc) || !object.Equals(entry[2], Call(doc, "IModelDoc2", "GetSaveFlag")) ||
                    !object.Equals(entry[3], TestConfiguration(doc)) ||
                    (!string.IsNullOrEmpty(file) && !string.Equals((string)entry[4], FileSha256(file), StringComparison.OrdinalIgnoreCase)))
                    throw new Fault("TEST_PROTECTED_DOCUMENT_CHANGED", "An unrelated document changed or closed; stop and inspect: " + file);
            }
        }

        void TestLoadedScope(string root, object doc)
        {
            TestFile(root, Text(Call(doc, "IModelDoc2", "GetPathName")));
            int type = Convert.ToInt32(Call(doc, "IModelDoc2", "GetType"));
            if (type != 2) return;
            var components = Call(doc, "IAssemblyDoc", "GetComponents", false) as Array;
            if (components == null) throw new Fault("TEST_COMPONENTS_UNKNOWN", "Cannot verify assembly components.");
            foreach (object component in components)
            {
                TestFile(root, Text(Call(component, "IComponent2", "GetPathName")));
                if (!object.Equals(Get(component, "IComponent2", "IsVirtual"), false))
                    throw new Fault("TEST_VIRTUAL_COMPONENT", "Virtual or unknown component identity is not supported.");
                object child = Call(component, "IComponent2", "GetModelDoc2");
                if (child != null) TestFile(root, Text(Call(child, "IModelDoc2", "GetPathName")));
            }
        }

        string TestConfiguration(object doc)
        {
            return Convert.ToInt32(Call(doc, "IModelDoc2", "GetType")) == 3 ? null : ActiveConfigurationOf(doc);
        }

        int TestActivate(string file)
        {
            object doc = Call(app, "ISldWorks", "GetOpenDocumentByName", file);
            if (doc == null) throw new Fault("TEST_DOCUMENT_NOT_OPEN", "Use operation=open first: " + file);
            object[] activate = { Text(Call(doc, "IModelDoc2", "GetTitle")), false,
                EnumValue("swRebuildOnActivation_e", "swDontRebuildActiveDoc"), 0 };
            object active = Call(app, "ISldWorks", "ActivateDoc3", activate);
            int activationCode = Convert.ToInt32(activate[3]);
            if (active == null || (activationCode != 0 && activationCode != EnumValue("swActivateDocError_e", "swDocNeedsRebuildWarning")))
                throw new Fault("TEST_ACTIVATE_FAILED", "Activation without rebuild returned code=" + activate[3] + "; document_returned=" + (active != null));
            Document();
            if (!string.Equals(file, path, StringComparison.OrdinalIgnoreCase)) throw new Fault("TEST_TARGET_CHANGED", "Unexpected active path.");
            int expectedKind = Path.GetExtension(file).Equals(".SLDASM", StringComparison.OrdinalIgnoreCase) ? 2 : 1;
            if (kind != expectedKind) throw new Fault("TEST_DOCUMENT_TYPE", "Loaded document type does not match its file extension.");
            return activationCode;
        }

        void TestTargetUnchanged(string root)
        {
            RequireWriteTargetUnchanged();
            if (string.IsNullOrEmpty(config) || !string.Equals(config, ActiveConfigurationOf(model), StringComparison.Ordinal))
                throw new Fault("CONFIGURATION_CHANGED", "Experiment configuration changed.");
            TestClosure(root, path);
            TestLoadedScope(root, model);
        }

        object TestHealth(object doc)
        {
            var rows = new List<object>(); var seen = new HashSet<object>();
            var pending = new Stack<object>();
            object first = Call(doc, "IModelDoc2", "IFirstFeature"); if (first != null) pending.Push(first);
            int errors = 0, warnings = 0, mates = 0;
            while (pending.Count > 0)
            {
                object feature = pending.Pop(); if (!seen.Add(feature)) continue;
                if (seen.Count > 2000) throw new Fault("TEST_FEATURE_LIMIT", "Incomplete feature/mate inventory.");
                string name = Text(Get(feature, "IFeature", "Name"));
                string type = Text(Call(feature, "IFeature", "GetTypeName2"));
                bool suppressed = FeatureSuppressed(feature);
                object[] errorArgs = { false };
                int code = Convert.ToInt32(Call(feature, "IFeature", "GetErrorCode2", errorArgs));
                bool warning = Convert.ToBoolean(errorArgs[0]);
                bool mate = type != null && type.StartsWith("Mate", StringComparison.Ordinal) &&
                    type != "MaterialFolder" && type != "MateGroup" && type != "MateReference";
                if (mate) mates++;
                if (!suppressed && code != 0) { if (warning) warnings++; else errors++; }
                rows.Add(Json.Obj("name", name, "type", type, "suppressed", suppressed, "code", code,
                    "is_warning", warning, "is_mate", mate, "api", "IFeature.GetErrorCode2"));
                object next = Call(feature, "IFeature", "GetNextFeature"); if (next != null) pending.Push(next);
                object sub = Call(feature, "IFeature", "GetFirstSubFeature");
                int subGuard = 0;
                while (sub != null)
                {
                    if (++subGuard > 2000) throw new Fault("TEST_FEATURE_LIMIT", "Subfeature traversal did not terminate.");
                    pending.Push(sub); sub = Call(sub, "IFeature", "GetNextSubFeature");
                }
            }
            return Json.Obj("status", errors == 0 && warnings == 0 ? "PASS" : "ISSUES",
                "error_count", errors, "warning_count", warnings, "mate_count", mates, "items", rows.ToArray(),
                "scope", "Feature and mate solver error/warning codes, not collision or engineering approval.");
        }

        object TestGeometry(object doc)
        {
            var bodies = Call(doc, "IPartDoc", "GetBodies2", EnumValue("swBodyType_e", "swSolidBody"), false) as Array;
            double volume = VolumeOf(doc);
            return Json.Obj("solid_body_count", bodies == null ? 0 : bodies.Length,
                "volume_m3", volume,
                "bounding_box_m", Call(doc, "IPartDoc", "GetPartBox", true), "bounding_box_approximate", true);
        }

        object TestAudit(string root)
        {
            TestTargetUnchanged(root);
            var components = new List<object>();
            object geometry = kind == 1 ? TestGeometry(model) : null;
            object health = TestHealth(model);
            if (kind == 2)
            {
                foreach (object component in (Array)Call(model, "IAssemblyDoc", "GetComponents", false))
                {
                    int state = Convert.ToInt32(Call(component, "IComponent2", "GetSuppression2"));
                    object child = Call(component, "IComponent2", "GetModelDoc2");
                    string childConfig = Text(Get(component, "IComponent2", "ReferencedConfiguration"));
                    bool matched = child != null && string.Equals(childConfig, ActiveConfigurationOf(child), StringComparison.Ordinal);
                    object childGeometry = matched && Convert.ToInt32(Call(child, "IModelDoc2", "GetType")) == 1 ? TestGeometry(child) : null;
                    object childHealth = matched ? TestHealth(child) : null;
                    if (matched && !string.Equals(childConfig, ActiveConfigurationOf(child), StringComparison.Ordinal))
                        throw new Fault("CONFIGURATION_CHANGED", "Component configuration changed during audit.");
                    object transform = Try("component.transform", delegate { return Get(component, "IComponent2", "Transform2"); });
                    object[] positionM = null;
                    if (transform != null)
                    {
                        var arrayData = Get(transform, "IMathTransform", "ArrayData") as Array;
                        if (arrayData != null && arrayData.Length >= 12)
                            positionM = new object[] {
                                Convert.ToDouble(arrayData.GetValue(9), CultureInfo.InvariantCulture),
                                Convert.ToDouble(arrayData.GetValue(10), CultureInfo.InvariantCulture),
                                Convert.ToDouble(arrayData.GetValue(11), CultureInfo.InvariantCulture) };
                    }
                    components.Add(Json.Obj("instance_id", Get(component, "IComponent2", "Name2"),
                        "path", Call(component, "IComponent2", "GetPathName"), "configuration", childConfig,
                        "suppression_state_code", state, "resolved_configuration_match", matched,
                        "geometry", childGeometry, "health", childHealth,
                        "assembly_position_xyz_m", positionM,
                        "assembly_position_source", positionM == null ? null : "IComponent2.Transform2.ArrayData[9..11]"));
                }
            }
            TestTargetUnchanged(root);
            return Json.Obj("file_path", path, "configuration", config, "has_unsaved_changes", Call(model, "IModelDoc2", "GetSaveFlag"),
                "health", health, "geometry", geometry, "components", components.ToArray(), "issues", issues.ToArray(),
                "manufacturing_approved", false);
        }

        void TestNoOpenReferrers(string file)
        {
            foreach (object doc in TestOpenDocuments())
            {
                string other = Text(Call(doc, "IModelDoc2", "GetPathName"));
                if (string.Equals(other, file, StringComparison.OrdinalIgnoreCase)) continue;
                // Unknown unsaved referrers cannot establish a genuine unload.
                if (string.IsNullOrEmpty(other)) throw new Fault("TEST_UNSAVED_REFERRER", "An unrelated unsaved document prevents a proven unload.");
                var dependencies = Call(doc, "IModelDoc2", "GetDependencies2", true, false, false) as Array;
                int count = Convert.ToInt32(Call(doc, "IModelDoc2", "GetNumDependencies", 1, 0));
                if (dependencies == null && count != 0) throw new Fault("TEST_REFERRERS_UNKNOWN", "Cannot establish open referrers.");
                if (dependencies != null) foreach (object dependency in dependencies)
                    if (string.Equals(Text(dependency), file, StringComparison.OrdinalIgnoreCase))
                        throw new Fault("TEST_DOCUMENT_REFERENCED", "Close the referencing test assembly explicitly first: " + other);
            }
        }

        object TestDocument(Dictionary<string, object> args)
        {
            string root = TestRoot(args);
            string file = TestFile(root, Catalog.LocalAnyDocumentPathText(args, "file_path"));
            string operation = Catalog.TextValue(args, "operation", true, 32);
            return TestDocumentCore(root, file, operation);
        }

        object TestDocumentCore(string root, string file, string operation)
        {
            var closure = TestClosure(root, file);
            var protectedDocs = TestProtectDocuments(closure);
            try
            {
                object open = null;
                if (operation == "open")
                    open = Call(app, "ISldWorks", "GetOpenDocumentByName", file) == null
                        ? OpenLocalPath(file, true, false, true)
                        : Json.Obj("open_status", "REUSED_ALREADY_LOADED_NOT_FRESH");
                int activationCode = TestActivate(file);
                TestTargetUnchanged(root);
                if (operation == "audit" || operation == "open")
                    return Json.Obj("operation", operation, "audit", TestAudit(root), "activation_code", activationCode,
                        "activation_requires_rebuild", activationCode != 0,
                        "fresh_open", open == null ? null : Json.At(Json.Map(open), "open_status"));
                if (operation == "rebuild_save")
                {
                    RequireWritableDocument();
                    var backups = new List<object>();
                    foreach (string item in closure) backups.Add(Json.Obj("source", item, "backup", CreateLocalBackup(item, "_BEFORE_TEST_REBUILD")));
                    TestTargetUnchanged(root);
                    if (kind == 2) Call(model, "IAssemblyDoc", "ResolveAllLightWeightComponents", false);
                    TestTargetUnchanged(root);
                    bool rebuilt = Convert.ToBoolean(Call(model, "IModelDoc2", "EditRebuild3"));
                    if (!rebuilt) throw new Fault("TEST_REBUILD_FAILED", "Rebuild failed; no document was saved. Backups retained.");
                    object audit = TestAudit(root);
                    if (!object.Equals(Json.At(Json.Map(Json.At(Json.Map(audit), "health")), "status"), "PASS"))
                        throw new Fault("TEST_FEATURE_ERRORS", "Feature or mate errors/warnings remain; no save performed.");
                    foreach (object row in (object[])Json.At(Json.Map(audit), "components"))
                    {
                        var componentAudit = Json.Map(row);
                        if (!object.Equals(Json.At(componentAudit, "resolved_configuration_match"), true) ||
                            !object.Equals(Json.At(Json.Map(Json.At(componentAudit, "health")), "status"), "PASS"))
                            throw new Fault("TEST_COMPONENT_HEALTH_UNKNOWN", "A component is unresolved or has feature issues; no save performed.");
                    }
                    TestTargetUnchanged(root);
                    object[] saveArgs = { EnumValue("swSaveAsOptions_e", "swSaveAsOptions_Silent"), 0, 0 };
                    bool saved = Convert.ToBoolean(Call(model, "IModelDoc2", "Save3", saveArgs));
                    TestTargetUnchanged(root);
                    if (!saved || Convert.ToInt32(saveArgs[1]) != 0 || Convert.ToInt32(saveArgs[2]) != 0 ||
                        !object.Equals(Call(model, "IModelDoc2", "GetSaveFlag"), false))
                        throw new Fault("TEST_SAVE_FAILED", "Save did not finish cleanly; backups retained.");
                    return Json.Obj("operation", operation, "rebuilt", true, "saved", true, "backups", backups.ToArray(),
                        "save_errors", saveArgs[1], "save_warnings", saveArgs[2], "audit", TestAudit(root));
                }
                if (operation != "close" && operation != "reopen") throw new Fault("INVALID_ARGUMENTS", "Unknown test operation.");
                if (activationCode != 0) throw new Fault("TEST_REBUILD_REQUIRED", "Rebuild and save the test document before closing.");
                if (!object.Equals(Call(model, "IModelDoc2", "GetSaveFlag"), false))
                    throw new Fault("TEST_DIRTY_CLOSE_BLOCKED", "Save the explicitly targeted test document first; unsaved changes will not be discarded.");
                TestNoOpenReferrers(file);
                foreach (string item in closure)
                {
                    object child = Call(app, "ISldWorks", "GetOpenDocumentByName", item);
                    if (child != null && !object.Equals(Call(child, "IModelDoc2", "GetSaveFlag"), false))
                        throw new Fault("TEST_DIRTY_CLOSE_BLOCKED", "A loaded dependency has unsaved changes: " + item);
                }
                string hash = FileSha256(file);
                TestTargetUnchanged(root);
                Call(app, "ISldWorks", "CloseDoc", title);
                model = null;
                if (Call(app, "ISldWorks", "GetOpenDocumentByName", file) != null)
                    throw new Fault("TEST_DOCUMENT_NOT_UNLOADED", "Document remains in memory; fresh reload is not proved.");
                if (!string.Equals(hash, FileSha256(file), StringComparison.OrdinalIgnoreCase))
                    throw new Fault("TEST_FILE_CHANGED_ON_CLOSE", "File changed during close.");
                if (operation == "close") return Json.Obj("operation", "closed", "file_path", file, "unloaded", true, "sha256", hash);
                object reopened = OpenLocalPath(file, true, false, true);
                TestActivate(file);
                if (!string.Equals(hash, FileSha256(file), StringComparison.OrdinalIgnoreCase))
                    throw new Fault("TEST_FILE_CHANGED_ON_OPEN", "File changed during open.");
                return Json.Obj("operation", "reopened", "unloaded_before_open", true, "sha256", hash,
                    "open_status", Json.At(Json.Map(reopened), "open_status"), "audit", TestAudit(root));
            }
            finally { TestVerifyProtected(protectedDocs); }
        }

        string TestPackOutputFile(string root, string candidate, bool allowDrawing)
        {
            if (!TestPathInside(root, candidate)) throw new Fault("TEST_SCOPE_ESCAPE", "File is outside the registered test folder: " + candidate);
            string value = Program.RequireLocalFixedPath(candidate, true);
            string ext = Path.GetExtension(value);
            bool ok = ext.Equals(".SLDPRT", StringComparison.OrdinalIgnoreCase) || ext.Equals(".SLDASM", StringComparison.OrdinalIgnoreCase) ||
                (allowDrawing && ext.Equals(".SLDDRW", StringComparison.OrdinalIgnoreCase));
            if (!ok) throw new Fault("TEST_DOCUMENT_TYPE", allowDrawing
                ? "Only test SLDPRT, SLDASM and SLDDRW files are supported."
                : "Only test SLDPRT and SLDASM files are supported.");
            return value;
        }

        object TestPackAndGo(Dictionary<string, object> args)
        {
            string root = TestRoot(args);
            string source = TestFile(root, Catalog.LocalAssemblyPathText(args, "file_path"));
            object rawIncludeDrawings;
            bool includeDrawings = args.TryGetValue("include_drawings", out rawIncludeDrawings) &&
                rawIncludeDrawings != null && Convert.ToBoolean(rawIncludeDrawings, CultureInfo.InvariantCulture);
            object doc = Call(app, "ISldWorks", "GetOpenDocumentByName", source);
            if (doc == null) throw new Fault("TEST_SOURCE_NOT_LOADED", "Pack and Go source must already be loaded; nothing was opened or activated.");
            string actualSource = Text(Call(doc, "IModelDoc2", "GetPathName"));
            if (!string.Equals(actualSource, source, StringComparison.OrdinalIgnoreCase))
                throw new Fault("TEST_SOURCE_IDENTITY", "Loaded document differs from requested source: " + actualSource);
            bool sourceDirty = Convert.ToBoolean(Call(doc, "IModelDoc2", "GetSaveFlag"));
            var protectedDocs = TestProtectDocuments(new HashSet<string>(StringComparer.OrdinalIgnoreCase));
            try
            {
                TestActivate(source);
                object extension = Get(doc, "IModelDoc2", "Extension");
                object pack = Call(extension, "IModelDocExtension", "GetPackAndGo");
                Set(pack, "IPackAndGo", "IncludeDrawings", includeDrawings);
                Set(pack, "IPackAndGo", "IncludeSimulationResults", false);
                Set(pack, "IPackAndGo", "IncludeSuppressed", true);
                Set(pack, "IPackAndGo", "IncludeToolboxComponents", true);
                object[] nameArgs = { null };
                if (!Convert.ToBoolean(Call(pack, "IPackAndGo", "GetDocumentNames", nameArgs)))
                    throw new Fault("TEST_PACK_INVENTORY", "Pack and Go did not return document names.");
                var names = nameArgs[0] as Array;
                int count = Convert.ToInt32(Call(pack, "IPackAndGo", "GetDocumentNamesCount"));
                if (names == null || names.Length != count || count < 1 || count > 250)
                    throw new Fault("TEST_PACK_INVENTORY", "Pack and Go document inventory is incomplete or too large.");
                string id = Guid.NewGuid().ToString("N").Substring(0, 12);
                string destination = Path.Combine(root, "Experiment_" + id);
                var outputs = new string[count]; var mapping = new List<object>();
                var sourceHashes = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase);
                var uniqueOutputs = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
                string assemblyOutput = null;
                for (int i = 0; i < count; i++)
                {
                    string input = Program.RequireLocalFixedPath(Text(names.GetValue(i)), true);
                    string ext = Path.GetExtension(input);
                    bool inputIsDrawing = ext.Equals(".SLDDRW", StringComparison.OrdinalIgnoreCase);
                    if (!ext.Equals(".SLDPRT", StringComparison.OrdinalIgnoreCase) && !ext.Equals(".SLDASM", StringComparison.OrdinalIgnoreCase) &&
                        !(includeDrawings && inputIsDrawing))
                        throw new Fault("TEST_PACK_FILE_TYPE", includeDrawings
                            ? "Only native parts, assemblies and their already-loaded drawings are copied."
                            : "Only native parts/assemblies are copied.");
                    object loaded = Call(app, "ISldWorks", "GetOpenDocumentByName", input);
                    object loadedDirty = loaded == null ? null : Call(loaded, "IModelDoc2", "GetSaveFlag");
                    sourceHashes.Add(input, FileSha256(input));
                    outputs[i] = Path.Combine(destination, "EXP_" + id + "_" + Path.GetFileName(input));
                    if (!uniqueOutputs.Add(outputs[i])) throw new Fault("TEST_PACK_NAME_COLLISION", "Duplicate file basenames are not safe to flatten.");
                    if (string.Equals(input, source, StringComparison.OrdinalIgnoreCase)) assemblyOutput = outputs[i];
                    mapping.Add(Json.Obj("source", input, "copy", outputs[i], "source_sha256", sourceHashes[input], "source_loaded_dirty", loadedDirty));
                }
                if (assemblyOutput == null) throw new Fault("TEST_PACK_INVENTORY", "Source assembly missing from Pack and Go inventory: " + Json.Encode(mapping.ToArray()));
                if (Directory.Exists(destination)) throw new Fault("TEST_OUTPUT_EXISTS", "Unique output already exists.");
                Directory.CreateDirectory(destination);
                Program.NoReparseAncestors(destination);
                if (!Convert.ToBoolean(Call(pack, "IPackAndGo", "SetDocumentSaveToNames", (object)outputs)))
                    throw new Fault("TEST_PACK_DESTINATIONS", "Pack and Go rejected destination names.");
                var statuses = Call(extension, "IModelDocExtension", "SavePackAndGo", pack) as Array;
                if (statuses == null || statuses.Length != count) throw new Fault("TEST_PACK_SAVE_FAILED", "Missing per-file Pack and Go status; partial output retained.");
                foreach (object status in statuses) if (Convert.ToInt32(status) != 0)
                    throw new Fault("TEST_PACK_SAVE_FAILED", "Pack and Go reported a failed file; partial output retained.");
                foreach (string output in outputs) TestPackOutputFile(root, output, includeDrawings);
                var closure = TestClosure(root, assemblyOutput);
                foreach (string dependency in closure) if (!uniqueOutputs.Contains(dependency))
                    throw new Fault("TEST_PACK_REFERENCE_ESCAPE", "Packed assembly still references a source document: " + dependency);
                foreach (var entry in sourceHashes) if (!string.Equals(entry.Value, FileSha256(entry.Key), StringComparison.OrdinalIgnoreCase))
                    throw new Fault("TEST_PACK_SOURCE_CHANGED", "Pack and Go changed a source file: " + entry.Key);
                return Json.Obj("operation", "PACKED_TEST_ASSEMBLY", "test_root", root, "folder", destination,
                    "assembly_path", assemblyOutput, "mapping", mapping.ToArray(), "verified_reference_count", closure.Count,
                    "include_drawings", includeDrawings, "source_files_unchanged", true, "source_had_unsaved_changes", sourceDirty,
                    "copy_basis", "Pack and Go output; validate the copied model after loading, not an assertion that unsaved source edits were serialized.",
                    "statuses", statuses, "manufacturing_approved", false);
            }
            finally { TestVerifyProtected(protectedDocs); }
        }
    }
}
