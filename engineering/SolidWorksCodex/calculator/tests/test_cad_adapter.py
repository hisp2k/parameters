"""Regression tests using the actual C# worker/read envelope, without CAD."""
from copy import deepcopy
import pytest
from calculator.cad_adapter.bridge_transport import BridgeResponse, FakeBridgeTransport, BridgeError
from calculator.cad_adapter.interface import LocalBridgeCadAdapter, ParameterMapEntry

SOURCE = r'C:\Models\source.SLDPRT'
VARIANT = r'C:\Models\source_VARIANT.SLDPRT'
NAME = 'AI_Length@Sketch1@source.SLDPRT'

def reply(tool, data, read=False):
    if read:
        data = {'data': data, 'partial': False, 'issues': [], 'context': {}}
    worker = {'ok': True, 'data': data}
    raw = {'ok': True, 'tool': tool, 'result': worker}
    return BridgeResponse.from_dict(raw)

def setup():
    doc = {'path': SOURCE, 'document_type': 'PART', 'connector_write_allowed': True, 'has_unsaved_changes': False}
    inv = {'items': [{'full_name': NAME, 'name': 'AI_Length', 'value_mm': 100, 'dimension_kind': 'LINEAR', 'editable_by_connector': True}], 'total': 1, 'partial': False, 'issues': []}
    variant = {'variant_path': VARIANT, 'source_path': SOURCE, 'source_unchanged': True,
               'source_sha256_before': 'abc', 'source_sha256_after': 'abc',
               'verification': {'status': 'PASS', 'rebuilt': True, 'all_requested_values_confirmed': True},
               'save': {'api_success': True, 'errors': 0, 'warnings': 0, 'file_path': VARIANT},
               'changes': [{'parameter_name': 'AI_Length', 'actual_mm': 120}]}
    t = FakeBridgeTransport({
        'sw_status': reply('sw_status', {'write_tools_available': ['sw_create_parameter_variant']}),
        'sw_document': reply('sw_document', doc, True),
        'sw_parameters': reply('sw_parameters', inv, True),
        'sw_create_parameter_variant': reply('sw_create_parameter_variant', variant),
    })
    return t, LocalBridgeCadAdapter(t), [ParameterMapEntry('length', NAME, 'mm')]

def test_reads_real_nested_inventory():
    t,a,m = setup()
    assert a.read_parameters(m) == {'length': 100}

def test_variant_uses_guarded_atomic_command_and_does_not_claim_acceptance():
    t,a,m = setup()
    r = a.rebuild_project_copy(m, {'length': 120}, source_path=SOURCE)
    assert r.parameter_update_verified and not r.ok and r.unknown_checks
    assert r.workspace_path == VARIANT
    assert t.calls[-1] == ('sw_create_parameter_variant', {'source_path': SOURCE, 'changes': [
        {'full_name': NAME, 'expected_current_mm': 100, 'new_value_mm': 120}]})
    assert [x[0] for x in t.calls] == ['sw_document', 'sw_parameters', 'sw_create_parameter_variant']

@pytest.mark.parametrize('field,value', [('partial', True), ('partial', None), ('issues', ['failed']), ('total', 2), ('total', True)])
def test_incomplete_inventory_never_writes(field,value):
    t,a,m = setup()
    t.responses['sw_parameters'].result['data']['data'][field] = value
    r=a.rebuild_project_copy(m, {'length':120}, source_path=SOURCE)
    assert not r.parameter_update_verified and r.errors
    assert 'sw_create_parameter_variant' not in [x[0] for x in t.calls]

@pytest.mark.parametrize('field,value', [('path',r'C:\other.SLDPRT'), ('document_type','ASSEMBLY'), ('connector_write_allowed',False), ('has_unsaved_changes',True), ('has_unsaved_changes',None)])
def test_source_identity_and_state_required(field,value):
    t,a,m=setup();t.responses['sw_document'].result['data']['data'][field]=value
    r=a.rebuild_project_copy(m,{'length':120},source_path=SOURCE)
    assert r.errors and not r.parameter_update_verified
    assert len(t.calls)==1

@pytest.mark.parametrize('value', [float('nan'),float('inf'),True,-1,2001,'120'])
def test_invalid_values_rejected_before_any_call(value):
    t,a,m=setup()
    with pytest.raises(ValueError): a.rebuild_project_copy(m,{'length':value},source_path=SOURCE)
    assert not t.calls

@pytest.mark.parametrize('tool,unit,name', [('sw_set_motion_parameter','mm',NAME),('sw_set_global_variable','mm',NAME),('sw_set_parameter','rad',NAME),('sw_set_parameter','mm','D1@Sketch1')])
def test_unsupported_writes_rejected(tool,unit,name):
    t,a,m=setup();m[0].write_tool=tool;m[0].unit=unit;m[0].solidworks_id=name
    with pytest.raises(ValueError): a.rebuild_project_copy(m,{'length':120},source_path=SOURCE)
    assert not t.calls

@pytest.mark.parametrize('field,value',[('source_unchanged',False),('variant_path',SOURCE),('source_sha256_after','changed'),('verification',{}),('save',{}),('changes',[]),('changes',[{'parameter_name':'wrong','actual_mm':120}]),('changes',[{'parameter_name':'AI_Length','actual_mm':119}])])
def test_unproven_write_result_is_not_success(field,value):
    t,a,m=setup();t.responses['sw_create_parameter_variant'].result['data'][field]=value
    r=a.rebuild_project_copy(m,{'length':120},source_path=SOURCE)
    assert r.errors and not r.ok and not r.parameter_update_verified

def test_noop_creates_no_duplicate_copy():
    t,a,m=setup();r=a.rebuild_project_copy(m,{'length':100},source_path=SOURCE)
    assert not r.ok and not r.parameter_update_verified
    assert len(t.calls)==2

def test_status_not_cached_after_disconnect():
    t,a,m=setup();assert a.can_read()
    t.responses.clear();assert not a.can_read()

def test_status_success_alone_does_not_prove_write_capability():
    t,a,m=setup();t.responses['sw_status']=reply('sw_status',{})
    assert a.can_read() and not a.can_write()

def test_old_assumed_envelope_rejected():
    t,a,m=setup();t.responses['sw_parameters']=BridgeResponse(True,'sw_parameters',{'data': {NAME:100}}, {})
    with pytest.raises(BridgeError): a.read_parameters(m)

def test_duplicate_inventory_rejected():
    t,a,m=setup();d=t.responses['sw_parameters'].result['data']['data'];d['items']*=2;d['total']=2
    with pytest.raises(BridgeError): a.read_parameters(m)
