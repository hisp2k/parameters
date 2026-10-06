using System;
using System.Text;
using System.Threading;

// Deterministic stand-in for SolidWorksLocal.exe used ONLY by
// RUN_CLAUDE_BRIDGE_TESTS.ps1 to test CLAUDE_CALL.ps1's own bridge logic
// (exit codes, request_id binding, atomic response, locking, timeout,
// stdout/stderr separation) without touching SOLIDWORKS or COM at all.
// Recognizes the same "--worker <tool> <base64 args>" calling convention as
// the real worker, and picks a canned, deterministic behavior from the tool
// name so every scenario is repeatable and fast.
internal static class FakeWorker
{
    static int Main(string[] args)
    {
        Console.OutputEncoding = new UTF8Encoding(false);
        if (args.Length != 3 || args[0] != "--worker")
        {
            Console.Error.WriteLine("FakeWorker: expected --worker <tool> <base64args>");
            return 9;
        }
        string tool = args[1];
        string argsJson = "{}";
        try { argsJson = Encoding.UTF8.GetString(Convert.FromBase64String(args[2])); } catch { }

        switch (tool)
        {
            case "fake_ok":
                Console.Out.Write("{\"ok\":true,\"data\":{\"echo\":" + JsonString(argsJson) + "}}");
                return 0;
            case "fake_fail":
                Console.Out.Write("{\"ok\":false,\"error\":{\"code\":\"FAKE_FAIL\",\"message\":\"simulated tool failure\"}}");
                return 0;
            case "fake_nonzero":
                // Deliberately prints a well-formed ok:true body but exits nonzero,
                // to check that the bridge does not blindly trust result.ok when the
                // process exit code disagrees with it.
                Console.Out.Write("{\"ok\":true,\"data\":{\"note\":\"this claims success but the process exit code says otherwise\"}}");
                return 3;
            case "fake_corrupt":
                Console.Out.Write("{ this is not valid JSON ][");
                return 0;
            case "fake_empty":
                return 0;
            case "fake_stderr_noise":
                Console.Error.WriteLine("diagnostic noise line 1");
                Console.Error.WriteLine("diagnostic noise line 2 with \"quotes\" and { braces }");
                Console.Out.Write("{\"ok\":true,\"data\":{\"note\":\"stdout stayed clean despite stderr noise\"}}");
                return 0;
            case "fake_hang":
                Thread.Sleep(300000);
                return 0;
            case "fake_delay_ok":
                int ms = 3000;
                int parsed;
                if (int.TryParse(Environment.GetEnvironmentVariable("FAKE_DELAY_MS"), out parsed)) ms = parsed;
                Thread.Sleep(ms);
                Console.Out.Write("{\"ok\":true,\"data\":{\"delayed_ms\":" + ms + "}}");
                return 0;
            default:
                Console.Out.Write("{\"ok\":false,\"error\":{\"code\":\"UNKNOWN_FAKE_TOOL\",\"message\":\"" + tool + "\"}}");
                return 0;
        }
    }

    static string JsonString(string s)
    {
        var sb = new StringBuilder();
        sb.Append('"');
        foreach (char c in s)
        {
            if (c == '"' || c == '\\') sb.Append('\\').Append(c);
            else if (c == '\n') sb.Append("\\n");
            else if (c == '\r') { }
            else sb.Append(c);
        }
        sb.Append('"');
        return sb.ToString();
    }
}
