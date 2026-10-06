using System;
using System.Runtime.CompilerServices;

// Loaded only by TEST_ASSEMBLY_READ_REGRESSIONS.ps1, never by the connector.
// Minimal managed doubles exercise the reader's real reflection dispatch without COM.
namespace SolidWorks.Interop.sldworks
{
    public class IConfiguration { public string Name { get; set; } }
    public class IConfigurationManager
    {
        public IConfiguration ActiveConfiguration { get; set; }
    }
    public class ICustomPropertyManager
    {
        public object GetNames() { return new string[0]; }
    }
    public class IMassProperty
    {
        public bool UseSystemUnits { get; set; }
        public double Mass { get { return 2.0; } }
        public double Volume { get { return 0.00025; } }
        public double SurfaceArea { get { return 0.1; } }
    }
    public class IModelDocExtension
    {
        public int MassReads;
        public Action AfterMassCreated;
        [IndexerName("CustomPropertyManager")]
        public ICustomPropertyManager this[string configuration]
        { get { return new ICustomPropertyManager(); } }
        public object CreateMassProperty()
        {
            MassReads++;
            if (AfterMassCreated != null) AfterMassCreated();
            return new IMassProperty();
        }
    }
    public class IModelDoc2
    {
        public IModelDoc2()
        {
            Extension = new IModelDocExtension();
            ConfigurationManager = new IConfigurationManager {
                ActiveConfiguration = new IConfiguration { Name = "A" }
            };
        }
        public IModelDocExtension Extension { get; set; }
        public IConfigurationManager ConfigurationManager { get; set; }
        // Used only by the OpenDoc6 fixtures below; defaults preserve the fixed values every other
        // (unrelated) fixture-based test already relies on from GetPathName()/GetType().
        public string PathName = @"C:\Pilot\Part.SLDPRT";
        public string Title = "Part";
        // null means "the API call itself is unavailable/throws", matching how a real
        // IsOpenedReadOnly() failure surfaces as UNKNOWN rather than a false boolean.
        public bool? ReadOnly;
        public int DocumentType = 1;
        public bool? Dirty = false;
        public int SaveCalls;
        public int RebuildCalls;
        public bool RebuildSuccess = true;
        public Action AfterRebuild;
        public IFeature FirstFeature;
        public IDimension ModelParameter;
        public object Dependencies;
        public int DependencyCount;
        public object GetDependencies2(bool traverse, bool search, bool readOnlyInfo) { return Dependencies; }
        public int GetNumDependencies(int traverse, int search) { return DependencyCount; }
        public bool GetSaveFlag()
        {
            if (!Dirty.HasValue) throw new InvalidOperationException("fixture: save flag unavailable");
            return Dirty.Value;
        }
        public bool Save3(int options, ref int errors, ref int warnings)
        { SaveCalls++; Dirty = false; return true; }
        public bool EditRebuild3()
        { RebuildCalls++; if (AfterRebuild != null) AfterRebuild(); return RebuildSuccess; }
        public void ClearSelection2(bool all) { }
        public object IFirstFeature() { return FirstFeature; }
        public object Parameter(string name) { return ModelParameter; }
        public new int GetType() { return DocumentType; }
        public string GetPathName() { return PathName; }
        public string GetTitle() { return Title; }
        public bool IsOpenedReadOnly()
        {
            if (!ReadOnly.HasValue) throw new InvalidOperationException("fixture: read-only state not configured for this test");
            return ReadOnly.Value;
        }
        public object GetEquationMgr() { return new IEquationMgr(); }
        public void ChangeConfigurationDuringMassRead()
        {
            Extension.AfterMassCreated = delegate { ConfigurationManager.ActiveConfiguration.Name = "B"; };
        }
    }
    public class IPartDoc : IModelDoc2
    {
        public object GetPartBox(bool noConversion) { return new double[] { 0, 0, 0, 0.1, 0.1, 0.1 }; }
        public object GetBodies2(int type, bool visibleOnly) { return new object[] { new object() }; }
        public string GetMaterialPropertyName2(string configuration, ref string database)
        { database = "fixture"; return "steel"; }
    }
    public class IDimension
    {
        public string Name { get; set; }
        public string FullName { get; set; }
        public bool ReadOnly { get; set; }
        public int DrivenState { get; set; }
        public int TypeCode = 0;
        public double Value = 0.01;
        public int SetCalls;
        public Action AfterSet;
        public int SetSystemValue3(double value, int configuration, object names)
        { SetCalls++; Value = value; if (AfterSet != null) AfterSet(); return 0; }
        public new int GetType() { return TypeCode; }
        public object GetSystemValue3(int configuration, object names) { return new[] { Value }; }
    }
    public class IDisplayDimension
    {
        public IDimension Dimension;
        public object GetDimension2(int index) { return Dimension; }
    }
    public class IFeature
    {
        public string Name { get; set; }
        public string TypeName = "Extrusion";
        public IFeature Next;
        public IDimension DirectDimension;
        public IDisplayDimension DisplayDimension;
        public object Suppression = new[] { false };
        public int ErrorCode;
        public bool ErrorIsWarning;
        public IFeature SubFeature;
        public int GetErrorCode2(ref bool warning) { warning = ErrorIsWarning; return ErrorCode; }
        public object GetFirstSubFeature() { return SubFeature; }
        public object GetNextSubFeature() { return null; }
        public string GetTypeName2() { return TypeName; }
        public object GetNextFeature() { return Next; }
        public object GetFirstDisplayDimension() { return DisplayDimension; }
        public object GetNextDisplayDimension(object current) { return null; }
        public object IsSuppressed2(int configuration, object names) { return Suppression; }
        public object Parameter(string name) { return DirectDimension; }
    }
    public class IComponent2
    {
        public string Name2 { get; set; }
        public string ReferencedConfiguration { get; set; }
        public bool IsVirtual { get; set; }
        public bool Suppressed;
        public IPartDoc Document;
        public string GetPathName() { return @"C:\Pilot\Part.SLDPRT"; }
        public int GetSuppression2() { return Suppressed ? 0 : 2; }
        public bool IsSuppressed() { return Suppressed; }
        public object GetModelDoc2() { return Document; }
        public object GetParent() { return null; }
    }
    public class IAssemblyDoc : IModelDoc2
    {
        public IComponent2 Component;
        public object GetComponents(bool topOnly) { return new[] { Component }; }
    }
    public class IEquationMgr
    {
        public int GetCount() { return 3; }
        [IndexerName("Equation")]
        public string this[int index] { get { return "\"L\" = 100"; } }
        public int GetConfigurationOption(int index) { return index + 1; }
    }
    // Exercises OpenLocalPath's real OpenDoc6/GetOpenDocumentByName/ActivateDoc2 dispatch
    // (reflection Call against by-ref Errors/Warnings/Errors out-parameters included) without COM.
    public class ISldWorks
    {
        public IModelDoc2 IActiveDoc2 { get; set; }
        public IModelDoc2 OpenDocResult;
        public int OpenDocErrors;
        public int OpenDocWarnings;
        public int OpenDocCallCount;
        public IModelDoc2 AlreadyOpenDocument;
        public IModelDoc2 ActivateResult;
        public int ActivateErrors;
        public string LastOpenDocFileName;
        public string LastActivateName;
        public IModelDoc2[] Documents;
        public int CloseCalls;
        public bool KeepDocumentLoaded;
        public object FileDependencies;
        public int FileDependencyCount;
        public object GetDocuments() { return Documents ?? new IModelDoc2[0]; }
        public int GetDocumentCount() { return Documents == null ? 0 : Documents.Length; }
        public object GetDocumentDependencies2(string path, bool traverse, bool search, bool readOnlyInfo) { return FileDependencies; }
        public int GetDocumentDependenciesCount(string path, int traverse, int search) { return FileDependencyCount; }
        public object ActivateDoc3(string name, bool preferences, int rebuild, ref int errors)
        { IActiveDoc2 = AlreadyOpenDocument; errors = ActivateErrors; return IActiveDoc2; }
        public void CloseDoc(string title)
        {
            CloseCalls++;
            if (!KeepDocumentLoaded) { AlreadyOpenDocument = null; Documents = new IModelDoc2[0]; }
        }
        public object OpenDoc6(string FileName, int Type, int Options, string Configuration, ref int Errors, ref int Warnings)
        {
            OpenDocCallCount++;
            LastOpenDocFileName = FileName;
            Errors = OpenDocErrors;
            Warnings = OpenDocWarnings;
            return OpenDocResult;
        }
        public object GetOpenDocumentByName(string FileName) { return AlreadyOpenDocument; }
        public object ActivateDoc2(string Name, bool UseUserPreferences, ref int Errors)
        {
            LastActivateName = Name;
            Errors = ActivateErrors;
            if (ActivateErrors != 0) return null;
            if (ActivateResult != null) return ActivateResult;
            return OpenDocResult ?? AlreadyOpenDocument;
        }
    }
}
namespace SolidWorks.Interop.swconst
{
    public enum swSaveAsOptions_e { swSaveAsOptions_Silent = 1 }
    public enum swRebuildOnActivation_e { swDontRebuildActiveDoc = 1 }
    public enum swActivateDocError_e { swGenericActivateError = 1, swDocNeedsRebuildWarning = 2 }
    public enum swSetValueInConfiguration_e { swSetValue_InThisConfiguration = 1 }
    public enum swBodyType_e { swSolidBody = 0 }
    public enum swInConfigurationOpts_e { swThisConfiguration = 1 }
    public enum swDimensionDrivenState_e { swDimensionDriving = 0 }
    public enum swDimensionType_e { swDimensionTypeUnknown = 0, swLinearDimension = 1, swAngularDimension = 3 }
    public enum swDimensionParamType_e
    {
        swDimensionParamTypeUnknown = -1, swDimensionParamTypeDoubleLinear = 0,
        swDimensionParamTypeDoubleAngular = 1, swDimensionParamTypeInteger = 2
    }
    public enum swComponentSuppressionState_e { swComponentLightweight = 1 }
    // Values are fixture-local flag bits, not the real SOLIDWORKS constants: OpenLocalPath only
    // ORs and forwards this value to OpenDoc6's Options parameter, which this fixture's ISldWorks
    // ignores; no test asserts on the actual numeric value.
    [Flags]
    public enum swOpenDocOptions_e { swOpenDocOptions_Silent = 1, swOpenDocOptions_ReadOnly = 2 }
}
