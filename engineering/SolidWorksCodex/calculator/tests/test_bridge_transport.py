"""Real PowerShell/process integration against a fake worker; never uses CAD."""
import json
import os
import shutil
import subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import pytest
from calculator.cad_adapter.bridge_transport import FileBridgeTransport, BridgeError, BridgeResponse

@pytest.fixture
def bridge(tmp_path):
    if os.name != 'nt': pytest.skip('Windows PowerShell integration')
    repo=Path(__file__).resolve().parents[2]
    shutil.copyfile(repo/'CLAUDE_CALL.ps1',tmp_path/'CLAUDE_CALL.ps1')
    compiler=Path(os.environ['WINDIR'])/'Microsoft.NET/Framework64/v4.0.30319/csc.exe'
    subprocess.run([str(compiler),'/nologo','/target:exe',f'/out:{tmp_path / "SolidWorksLocal.exe"}',str(repo/'FakeWorker.cs')],check=True,capture_output=True)
    return FileBridgeTransport(tmp_path)

def test_real_unicode_envelope(bridge):
    r=bridge.call('fake_ok',{'text':'Деталь №1'},5)
    assert r.ok and json.loads(r.result['data']['echo'])=={'text':'Деталь №1'}
    root=bridge.repo_root/'ClaudeBridge'
    assert len(list((root/'requests').glob('*.json')))==1
    assert not (root/'request.json').exists()

def test_simultaneous_requests_never_share_input_or_response(bridge):
    with ThreadPoolExecutor(max_workers=4) as pool:
        results=list(pool.map(lambda n: bridge.call('fake_ok',{'n':n},5), range(4)))
    assert len({r.raw['request_id'] for r in results})==4
    assert any(r.ok for r in results)
    for n,r in enumerate(results):
        if r.ok: assert json.loads(r.result['data']['echo'])=={'n':n}
        else: assert r.error['code']=='BRIDGE_BUSY'
    assert not (bridge.repo_root/'ClaudeBridge/worker.lock').exists()

def test_timeout_quarantines_writes_and_preserves_result(bridge):
    r=bridge.call('fake_hang',{},5)
    assert not r.ok and r.raw['status']=='UNKNOWN'
    assert r.error['code']=='TIMEOUT'
    r=bridge.call('fake_ok',{},5)
    assert not r.ok and r.error['code']=='QUARANTINED_AFTER_TIMEOUT'

def test_abandoned_lock_is_not_stolen(bridge):
    root=bridge.repo_root/'ClaudeBridge';root.mkdir()
    lock=root/'worker.lock';lock.write_text('pid=999999999\ntoken=preserve\n')
    r=bridge.call('fake_ok',{},5)
    assert not r.ok and r.error['code']=='BRIDGE_BUSY'
    assert lock.read_text()=='pid=999999999\ntoken=preserve\n'

def test_string_success_is_not_true():
    assert not BridgeResponse.from_dict({'ok':'false'}).ok

@pytest.mark.parametrize('bad',[{'request_id':'wrong'}, {'tool':'wrong'}, {'ok':'true'}, {'result':{} }])
def test_response_mismatch_rejected(tmp_path,monkeypatch,bad):
    (tmp_path/'CLAUDE_CALL.ps1').write_text('')
    monkeypatch.setattr('calculator.cad_adapter.bridge_transport.platform.system',lambda:'Windows')
    monkeypatch.setattr('calculator.cad_adapter.bridge_transport.shutil.which',lambda _: 'powershell')
    def run(args,**kwargs):
        req=json.loads(Path(args[-1]).read_text())
        raw={'ok':True,'request_id':req['request_id'],'tool':req['tool'],'result':{'ok':True,'data':{}}}
        raw.update(bad)
        out=tmp_path/'ClaudeBridge/responses';out.mkdir()
        (out/f'{req["request_id"]}.json').write_text(json.dumps(raw))
        return subprocess.CompletedProcess(args,0)
    monkeypatch.setattr('calculator.cad_adapter.bridge_transport.subprocess.run',run)
    with pytest.raises(BridgeError): FileBridgeTransport(tmp_path).call('fake_ok',{},5)
