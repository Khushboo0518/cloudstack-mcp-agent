from mcp.server.fastmcp import FastMCP
import requests
import hmac
import hashlib
import base64
import urllib.parse
import time

# CloudStack API configuration
API_URL = "http://localhost:8080/client/api"
API_KEY = "your_api-key"
SECRET_KEY = "your_secret_key"

mcp = FastMCP("VM-Manager")

def call_cloudstack_api(command: str, params: dict) -> dict:
    """
    Send a signed minimal POST request to CloudStack API (fixes 431).
    """
    # Clean None or empty values
    filtered = {k: str(v) for k, v in params.items() if v}
    filtered.update({
        "command": command,
        "apikey": API_KEY,
        "response": "json"
    })

    # Signature base
    sorted_params = sorted((k.lower(), v.lower()) for k, v in filtered.items())
    query_string = '&'.join(['='.join(map(urllib.parse.quote_plus, kv)) for kv in sorted_params])

    # HMAC-SHA1 signature
    signature = base64.b64encode(hmac.new(
        SECRET_KEY.encode('utf-8'),
        query_string.lower().encode('utf-8'),
        hashlib.sha1
    ).digest()).decode('utf-8')

    # Final request params
    filtered["signature"] = signature

    # Send POST request to avoid header/URL limits
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    response = requests.post(API_URL, data=filtered, headers=headers)
    response.raise_for_status()
    return response.json()

def poll_job(job_id: str, timeout: int = 60) -> dict:
    start_time = time.time()
    while time.time() - start_time < timeout:
        result = call_cloudstack_api("queryAsyncJobResult", {"jobid": job_id})
        job_status = result['queryasyncjobresultresponse']['jobstatus']
        if job_status == 1:
            return result['queryasyncjobresultresponse']['jobresult']
        elif job_status == 2:
            raise Exception(f"Job failed: {result}")
        time.sleep(2)
    raise TimeoutError(f"Job {job_id} did not complete within {timeout} seconds.")

def get_id_by_name(resource_list: list, name_key: str, target_name: str) -> str:
    for item in resource_list:
        if item[name_key].lower() == target_name.lower():
            return item['id']
    raise ValueError(f"{target_name} not found.")

# ── TOOLS ───────────────────────────────────────────────────────────────────────

@mcp.tool()
def deploy_vm_by_name(vm_name: str, zone_name: str, template_name: str, service_offering_name: str) -> str:
    try:
        zones = call_cloudstack_api("listZones", {})['listzonesresponse']['zone']
        zone_id = get_id_by_name(zones, "name", zone_name)

        templates = call_cloudstack_api("listTemplates", {"templatefilter": "featured"})['listtemplatesresponse']['template']
        template_id = get_id_by_name(templates, "name", template_name)

        offerings = call_cloudstack_api("listServiceOfferings", {})['listserviceofferingsresponse']['serviceoffering']
        offering_id = get_id_by_name(offerings, "name", service_offering_name)

        deploy_response = call_cloudstack_api("deployVirtualMachine", {
            "zoneid": zone_id,
            "templateid": template_id,
            "serviceofferingid": offering_id,
            "name": vm_name,
            "displayname": vm_name
        })
        job_id = deploy_response['deployvirtualmachineresponse']['jobid']
        print(f"VM deployment started. Job ID: {job_id}")

        vm_result = poll_job(job_id)
        vm = vm_result['virtualmachine']

        return (f"✅ VM Created Successfully!\n"
                f"Name: {vm['name']}\n"
                f"ID: {vm['id']}\n"
                f"Zone: {vm['zonename']}\n"
                f"IP Address: {vm['nic'][0]['ipaddress']}\n"
                f"State: {vm['state']}")
    except Exception as e:
        return f"❌ VM deployment failed: {str(e)}"

@mcp.tool()
def deploy_vm_auto(vm_name: str) -> str:
    """
    Automatically deploys a VM using the first available zone, template, and offering.
    """
    try:
        zone = call_cloudstack_api("listZones", {})['listzonesresponse']['zone'][0]
        template = call_cloudstack_api("listTemplates", {"templatefilter": "featured"})['listtemplatesresponse']['template'][0]
        offering = call_cloudstack_api("listServiceOfferings", {})['listserviceofferingsresponse']['serviceoffering'][0]

        return deploy_vm_by_name(vm_name, zone['name'], template['name'], offering['name'])
    except Exception as e:
        return f"❌ Auto VM deployment failed: {str(e)}"

@mcp.tool()
def delete_vm_by_name(vm_name: str) -> str:
    try:
        vms = call_cloudstack_api("listVirtualMachines", {})['listvirtualmachinesresponse']['virtualmachine']
        vm_id = get_id_by_name(vms, "name", vm_name)

        delete_response = call_cloudstack_api("destroyVirtualMachine", {
            "id": vm_id,
            "expunge": "true"
        })
        job_id = delete_response['destroyvirtualmachineresponse']['jobid']
        print(f"VM deletion started. Job ID: {job_id}")

        poll_job(job_id)
        return f"🗑 VM '{vm_name}' deleted successfully."
    except Exception as e:
        return f"❌ VM deletion failed: {str(e)}"

@mcp.tool()
def list_vms(state_filter: str = "all") -> str:
    try:
        vms_response = call_cloudstack_api("listVirtualMachines", {})
        vms = vms_response['listvirtualmachinesresponse'].get('virtualmachine', [])
        if not vms:
            return "📭 No user VMs found."

        if state_filter.lower() != "all":
            vms = [vm for vm in vms if vm['state'].lower() == state_filter.lower()]
            if not vms:
                return f"📭 No user VMs found in state: {state_filter}."

        result = f"📄 *User VMs ({state_filter.title()}):*\n"
        for vm in vms:
            nic_ip = vm['nic'][0]['ipaddress'] if vm.get('nic') else "N/A"
            result += (f"- 🖥 Name: {vm['name']}\n"
                       f"  🆔 ID: {vm['id']}\n"
                       f"  🌐 Zone: {vm['zonename']}\n"
                       f"  ⚡ State: {vm['state']}\n"
                       f"  📡 IP: {nic_ip}\n\n")
        return result.strip()
    except Exception as e:
        return f"❌ Failed to list user VMs: {str(e)}"

@mcp.tool()
def list_system_vms() -> str:
    try:
        sys_vms_response = call_cloudstack_api("listSystemVms", {})
        sys_vms = sys_vms_response['listsystemvmsresponse'].get('systemvm', [])
        if not sys_vms:
            return "📭 No system VMs found."

        result = "🛠 *System VMs:*\n"
        for vm in sys_vms:
            result += (f"- 🖥 Name: {vm['name']}\n"
                       f"  🆔 ID: {vm['id']}\n"
                       f"  📡 IP: {vm.get('ipaddress', 'N/A')}\n"
                       f"  🔌 Type: {vm.get('systemvmtype', 'N/A')}\n"
                       f"  ⚡ State: {vm['state']}\n\n")
        return result.strip()
    except Exception as e:
        return f"❌ Failed to list system VMs: {str(e)}"

@mcp.tool()
def list_zones() -> str:
    try:
        zones = call_cloudstack_api("listZones", {})['listzonesresponse'].get('zone', [])
        return "\n".join(f"🗺 Zone: {z['name']} (ID: {z['id']})" for z in zones) or "📭 No zones found."
    except Exception as e:
        return f"❌ Failed to list zones: {str(e)}"

@mcp.tool()
def list_templates() -> str:
    try:
        templates = call_cloudstack_api("listTemplates", {"templatefilter": "featured"})['listtemplatesresponse'].get('template', [])
        return "\n".join(f"📦 Template: {t['name']} (ID: {t['id']})" for t in templates) or "📭 No templates found."
    except Exception as e:
        return f"❌ Failed to list templates: {str(e)}"

@mcp.tool()
def list_service_offerings() -> str:
    try:
        offerings = call_cloudstack_api("listServiceOfferings", {})['listserviceofferingsresponse'].get('serviceoffering', [])
        return "\n".join(f"⚙️ Offering: {o['name']} (ID: {o['id']})" for o in offerings) or "📭 No service offerings found."
    except Exception as e:
        return f"❌ Failed to list service offerings: {str(e)}"

# ── ENTRY ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    mcp.run()
