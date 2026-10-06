using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Reflection;
using System.Runtime.InteropServices;
using System.Text;
using System.Threading.Tasks;

[assembly: AssemblyTitle("SolidWorks Local MCP")]
[assembly: AssemblyVersion("2.5.0.0")]
[assembly: AssemblyFileVersion("2.5.0.0")]

namespace SolidWorksLocal
{
    internal static class Program
    {
        internal const string Version = "2.5.0";
        internal static readonly UTF8Encoding Utf8 = new UTF8Encoding(false);

        internal static Dictionary<string, object> Unwrap(Exception e)
        {
            while (e is TargetInvocationException && e.InnerException != null) e = e.InnerException;
            var f = e as Fault;
            string hint = null;
            if (e is COMException)
            {
                hint = "Откройте SOLIDWORKS и закройте модальные диалоги. Codex и SOLIDWORKS должны работать от одного пользователя и с одинаковым уровнем прав (обычно без администратора). Повторите запрос после завершения текущей операции.";
            }
            return Json.Obj("code", f == null ? "API_OR_RUNTIME_ERROR" : f.Code, "message", e.Message,
                "type", e.GetType().FullName, "hresult", "0x" + e.HResult.ToString("X8"), "hint", hint);
        }
        internal static string Root { get { return AppDomain.CurrentDomain.BaseDirectory; } }
        internal static string WorkspaceRoot
        {
            get { return Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "SolidWorksCodex", "Workspace"); }
        }
        internal static void NoReparseAncestors(string path)
        {
            var dir = new DirectoryInfo(Path.GetFullPath(path));
            while (dir != null)
            {
                if (dir.Exists && (dir.Attributes & FileAttributes.ReparsePoint) != 0)
                    throw new Fault("REPARSE_PATH_BLOCKED", "Use an ordinary local folder; symbolic links and junctions are not supported.");
                dir = dir.Parent;
            }
        }
        internal static bool IsNetworkOrDevicePathText(string path)
        {
            if (string.IsNullOrWhiteSpace(path)) return false;
            string value = path.Trim();
            return value.StartsWith(@"\\", StringComparison.Ordinal) ||
                value.StartsWith("//", StringComparison.Ordinal);
        }
        internal static bool IsWritableLocalDriveType(DriveType driveType)
        {
            return driveType == DriveType.Fixed;
        }
        internal static bool PdmVaultNameMeansBlocked(string vaultName)
        {
            return !string.IsNullOrWhiteSpace(vaultName);
        }
        internal static void RejectPdmVaultPath(string path)
        {
            Type type;
            try { type = Type.GetTypeFromProgID("ConisioLib.EdmVault", false); }
            catch { type = null; }
            if (type == null) return;

            object vault = null;
            try
            {
                vault = Activator.CreateInstance(type);
                object value = vault.GetType().InvokeMember("GetVaultNameFromPath", BindingFlags.InvokeMethod,
                    null, vault, new object[] { path });
                if (PdmVaultNameMeansBlocked(Convert.ToString(value)))
                    throw new Fault("PDM_VAULT_PATH_BLOCKED", "Files inside a SOLIDWORKS PDM vault view are blocked. Copy the file to an ordinary local folder first.");
            }
            catch (Fault) { throw; }
            // Some PDM client installations register ConisioLib.EdmVault but do
            // not expose GetVaultNameFromPath through late-bound COM. That is not
            // evidence that an ordinary local folder belongs to a vault. Keep the
            // fixed-drive/network/reparse checks authoritative and fail open only
            // for this optional extra PDM classification probe.
            catch { return; }
            finally
            {
                if (vault != null && Marshal.IsComObject(vault))
                {
                    try { Marshal.FinalReleaseComObject(vault); }
                    catch { }
                }
            }
        }
        internal static string RequireLocalFixedPath(string path, bool mustExist)
        {
            if (string.IsNullOrWhiteSpace(path) || IsNetworkOrDevicePathText(path))
                throw new Fault("NETWORK_PATH_BLOCKED", "Only files on a local fixed disk are allowed. UNC, device and network paths are blocked.");
            if (!Path.IsPathRooted(path))
                throw new Fault("LOCAL_ABSOLUTE_PATH_REQUIRED", "A saved file with an absolute local path is required.");
            string full = Path.GetFullPath(path);
            string root = Path.GetPathRoot(full);
            if (string.IsNullOrWhiteSpace(root))
                throw new Fault("LOCAL_FIXED_DRIVE_REQUIRED", "Cannot determine the local drive for the document.");
            DriveInfo drive;
            try { drive = new DriveInfo(root); }
            catch { throw new Fault("LOCAL_FIXED_DRIVE_REQUIRED", "Cannot verify the document drive as a local fixed disk."); }
            try
            {
                if (!drive.IsReady || !IsWritableLocalDriveType(drive.DriveType))
                    throw new Fault("LOCAL_FIXED_DRIVE_REQUIRED", "Writing is allowed only on a ready local fixed disk. Network, removable, optical and RAM drives are blocked.");
            }
            catch (Fault) { throw; }
            catch { throw new Fault("LOCAL_FIXED_DRIVE_REQUIRED", "Cannot verify the document drive as a ready local fixed disk."); }
            string directory = Path.GetDirectoryName(full);
            if (string.IsNullOrWhiteSpace(directory) || !Directory.Exists(directory))
                throw new Fault("LOCAL_DIRECTORY_REQUIRED", "The local document folder does not exist.");
            NoReparseAncestors(directory);
            if (File.Exists(full) && (File.GetAttributes(full) & FileAttributes.ReparsePoint) != 0)
                throw new Fault("REPARSE_PATH_BLOCKED", "Symbolic links and reparse-point files are not supported.");
            if (mustExist && !File.Exists(full))
                throw new Fault("LOCAL_FILE_REQUIRED", "The saved local document file does not exist.");
            string pdmProbe = File.Exists(full) || Directory.Exists(full) ? full : directory;
            RejectPdmVaultPath(pdmProbe);
            return full;
        }
        internal static bool IsLocalFixedPath(string path, bool mustExist)
        {
            try { RequireLocalFixedPath(path, mustExist); return true; }
            catch { return false; }
        }
        internal static string EnsureWorkspace()
        {
            string root = Path.GetFullPath(WorkspaceRoot);
            if (new Uri(root).IsUnc) throw new Fault("LOCAL_WORKSPACE_REQUIRED", "The SOLIDWORKS workspace must be on this computer, not on a network path.");
            NoReparseAncestors(root);
            Directory.CreateDirectory(root);
            NoReparseAncestors(root);
            return root;
        }
        internal static bool IsWorkspacePath(string path)
        {
            if (string.IsNullOrWhiteSpace(path) || IsNetworkOrDevicePathText(path)) return false;
            string root = EnsureWorkspace();
            string full = Path.GetFullPath(path);
            if (!full.StartsWith(root + Path.DirectorySeparatorChar, StringComparison.OrdinalIgnoreCase)) return false;
            if (File.Exists(full) && (File.GetAttributes(full) & FileAttributes.ReparsePoint) != 0) return false;
            NoReparseAncestors(full);
            return true;
        }
        internal static string SaveReport(object content, string prefix)
        {
            if (prefix != "snapshot" && prefix != "check") throw new Fault("INVALID_REPORT_TYPE", "Unknown report type.");
            string dir = Path.Combine(Root, "Reports");
            NoReparseAncestors(dir);
            Directory.CreateDirectory(dir);
            NoReparseAncestors(dir);
            string path = Path.Combine(dir, prefix + "_" + DateTime.UtcNow.ToString("yyyyMMdd_HHmmss") + "_" + Guid.NewGuid().ToString("N") + ".json");
            using (var stream = new FileStream(path, FileMode.CreateNew, FileAccess.Write, FileShare.None))
            using (var writer = new StreamWriter(stream, Utf8)) writer.Write(Json.Encode(content));
            return path;
        }
        static ProcessStartInfo WorkerStart(string tool, Dictionary<string, object> args)
        {
            string executable = Assembly.GetExecutingAssembly().Location;
            string payload = Convert.ToBase64String(Utf8.GetBytes(Json.Encode(args)));
#if PORTABLE_TEST
            string host = Environment.ProcessPath;
            if (string.IsNullOrEmpty(host)) throw new Fault("TEST_HOST_MISSING", "Cannot locate the portable test host.");
            var start = new ProcessStartInfo(host, "\"" + executable + "\" --worker " + tool + " " + payload);
#else
            var start = new ProcessStartInfo(executable, "--worker " + tool + " " + payload);
#endif
            start.UseShellExecute = false;
            start.CreateNoWindow = true;
            start.RedirectStandardOutput = true;
            start.RedirectStandardError = true;
            start.StandardOutputEncoding = Utf8;
            start.StandardErrorEncoding = Utf8;
            start.WorkingDirectory = Root;
            return start;
        }
        internal static int WorkerTimeoutMilliseconds(string tool)
        {
            bool longOperation = tool == "sw_create_plate" || tool == "sw_create_part_from_plan" ||
                tool == "sw_create_sheet_from_contours" || tool == "sw_create_profile_part_from_plan" ||
                tool == "sw_create_turned_part_from_plan" || tool == "sw_create_drawing" ||
                tool == "sw_export_workspace_pdf" || tool == "sw_set_parameter" ||
                tool == "sw_set_parameters" || tool == "sw_set_feature_dimensions" ||
                tool == "sw_set_global_variable" ||
                tool == "sw_create_parameter_variant" || tool == "sw_open_assembly_readonly" ||
                tool == "sw_test_pack_and_go" || tool == "sw_test_document";
            // Mutex contention must not consume the actual COM operation's time budget.
            return SolidWorksReader.ComMutexTimeoutMs + (longOperation ? 55000 : 25000);
        }
        internal static object InvokeWorker(string tool, Dictionary<string, object> args)
        {
            Catalog.Validate(tool, args); // names cannot introduce executable arguments
            using (var p = new Process { StartInfo = WorkerStart(tool, args) })
            {
                if (!p.Start()) throw new Fault("WORKER_START_FAILED", "Cannot start the connector worker.");
                Task<string> stdout = p.StandardOutput.ReadToEndAsync();
                Task<string> stderr = p.StandardError.ReadToEndAsync();
                int timeoutMs = WorkerTimeoutMilliseconds(tool);
                if (!p.WaitForExit(timeoutMs))
                {
                    // Kill only this process, created by us, never SOLIDWORKS or a process tree.
                    try { p.Kill(); p.WaitForExit(2000); } catch { }
                    throw new Fault("SOLIDWORKS_TIMEOUT", "SOLIDWORKS не ответил за " + (timeoutMs / 1000) + " секунд. Закройте диалоги, дождитесь завершения операции и повторите запрос. SOLIDWORKS не был завершён; не повторяйте запросы подряд.");
                }
                string output = stdout.GetAwaiter().GetResult();
                string errors = stderr.GetAwaiter().GetResult();
                if (output.Length > 4 * 1024 * 1024) throw new Fault("OUTPUT_TOO_LARGE", "Use a smaller test model.");
                Dictionary<string, object> envelope;
                try { envelope = Json.Map(Json.Decode(output)); }
                catch { throw new Fault("WORKER_OUTPUT_INVALID", "Worker did not return JSON. Exit code: " + p.ExitCode + ". " + errors.Substring(0, Math.Min(2000, errors.Length))); }
                if (envelope == null) throw new Fault("WORKER_OUTPUT_INVALID", "No worker result.");
                if (!Object.Equals(Json.At(envelope, "ok"), true))
                {
                    var fault = Json.Map(Json.At(envelope, "error"));
                    throw new Fault((string)Json.At(fault, "code", "WORKER_FAILED"),
                        (string)Json.At(fault, "message", "Worker failed") + " " + (string)Json.At(fault, "hint", ""));
                }
                if (p.ExitCode != 0) throw new Fault("WORKER_EXIT_ERROR", "Unexpected exit code: " + p.ExitCode);
                object data = Json.At(envelope, "data");
                if (tool == "sw_export_snapshot")
                {
                    string path = SaveReport(data, "snapshot");
                    return Json.Obj("report_path", path, "format", "JSON", "snapshot", data);
                }
                return data;
            }
        }
        static int Check()
        {
            var check = Json.Obj("connector_version", Version, "captured_at_utc", DateTime.UtcNow.ToString("o"),
                "machine", Environment.MachineName, "windows", Environment.OSVersion.VersionString,
                "is64bit", Environment.Is64BitProcess, "runtime", Environment.Version.ToString(),
                "executable", Assembly.GetExecutingAssembly().Location, "live_solidworks_checked", true);
            bool ok = false;
            try
            {
                check.Add("connection", InvokeWorker("sw_status", Json.Obj()));
                check.Add("active_document", InvokeWorker("sw_document", Json.Obj()));
                ok = true;
            }
            catch (Exception ex) { check.Add("error", Unwrap(ex)); }
            check.Add("ok", ok);
            string path = SaveReport(check, "check");
            Console.WriteLine(ok ? "PASS: connection and active document read successfully." : "CHECK FAILED: see JSON report for details.");
            Console.WriteLine("Report: " + path);
            return ok ? 0 : 2;
        }
        [STAThread]
        public static int Main(string[] args)
        {
            Console.InputEncoding = Utf8;
            Console.OutputEncoding = Utf8;
            try
            {
                if (args.Length == 1 && args[0] == "--stdio")
                {
                    new Protocol(InvokeWorker).Run(Console.In, Console.Out); return 0;
                }
                if (args.Length == 3 && args[0] == "--worker")
                {
                    try
                    {
                        var a = Json.Map(Json.Decode(Utf8.GetString(Convert.FromBase64String(args[2]))));
                        var data = SolidWorksReader.Read(args[1], a);
                        Console.WriteLine(Json.Encode(Json.Obj("ok", true, "data", data))); return 0;
                    }
                    catch (Exception ex) { Console.WriteLine(Json.Encode(Json.Obj("ok", false, "error", Unwrap(ex)))); return 2; }
                }
                if (args.Length == 1 && args[0] == "--check") return Check();
                if (args.Length == 1 && args[0] == "--self-test") return Tests.Run();
                Console.Error.WriteLine("SolidWorks Local MCP " + Version + ": --stdio (Codex), --check (Windows diagnostic), --self-test (offline tests).");
                return args.Length == 0 ? 0 : 2;
            }
            catch (Exception ex) { Console.Error.WriteLine(Json.Encode(Unwrap(ex))); return 2; }
        }
    }
}
