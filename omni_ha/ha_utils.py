from requests import post
from homeassistant_api import Client

def get_ha_devices(ha_url, token, only_available=True):
    """获取Home Assistant中的设备列表，排除纯更新服务和纯传感器设备
    
    Args:
        host (str): HA服务器地址
        port (int): HA服务器端口
        token (str): HA长期访问令牌
    
    Returns:
        list: 包含可控制设备信息的列表，每个元素为 (device_id, device_name) 元组
    """ 
    
    headers = {
        "Authorization": f"Bearer {token}",
        "content-type": "application/json",
    }
    
    template = """
    {% set devices = states | map(attribute="entity_id") | map("device_id") | unique | reject("eq",None) | list %}
    {%- set ns = namespace(devices = []) %}
    {%- for device in devices %}
    {%- set entities = device_entities(device) | list %}
    {%- if entities %}
    {%- set ns.devices = ns.devices + [ {
        device: {
            "name": device_attr(device, "name"),
            "name_by_user": device_attr(device, "name_by_user"),
            "model": device_attr(device, "model"),
            "manufacturer": device_attr(device, "manufacturer"),
            "hw_version": device_attr(device, "hw_version"),
            "sw_version": device_attr(device, "sw_version"),
            "configuration_url": device_attr(device, "configuration_url"),
            "entry_type": device_attr(device, "entry_type"),
            "disabled_by": device_attr(device, "disabled_by"),
            "area_id": device_attr(device, "area_id"),
            "suggested_area": device_attr(device, "suggested_area"),
            "via_device_id": device_attr(device, "via_device_id"),
            "identifiers": device_attr(device, "identifiers") | list,
            "connections": device_attr(device, "connections") | list,
            "entities": entities
        }
    } ] %}
    {%- endif %}
    {%- endfor %}
    {{ ns.devices | tojson }}
    """
    
    url = f"{ha_url}/api/template"
    
    # Assigns the Client object to a variable and checks if it's running.
    client = Client(f'{ha_url}/api', token)
    response = post(url, headers=headers, json={"template": template.strip()})
    data = response.json()
    
    result = []
    # 检查返回的数据是否为字符串，如果是则需要解析
    if isinstance(data, str):
        import json
        try:
            data = json.loads(data)
        except json.JSONDecodeError:
            print("无法解析返回的数据")
            return []
    for device in data:
        for device_id, device_info in device.items():
            device_name = device_info['name']
            name_by_user = device_info.get('name_by_user', '')
            model = device_info.get('model', '')
            manufacturer = device_info.get('manufacturer', '')
            hw_version = device_info.get('hw_version', '')
            sw_version = device_info.get('sw_version', '')
            configuration_url = device_info.get('configuration_url', '')
            entry_type = device_info.get('entry_type', '')
            disabled_by = device_info.get('disabled_by', '')
            area_id = device_info.get('area_id', '')
            suggested_area = device_info.get('suggested_area', '')
            via_device_id = device_info.get('via_device_id', '')
            identifiers = device_info.get('identifiers', [])
            connections = device_info.get('connections', [])
            entities = device_info['entities']
            
            # 跳过更新服务
            if len(entities) == 1 and entities[0].startswith('update.'):
                continue

            # 跳过纯传感器设备
            is_sensor = True
            for entity_id in entities:
                if not entity_id.startswith('sensor.'):
                    is_sensor = False
                    break
            if is_sensor:
                continue
            # 打印设备详细信息
            # print(f"设备名称: {device_name}")
            # print(f"用户设定名称: {name_by_user}")
            # print(f"型号: {model}")
            # print(f"制造商: {manufacturer}")
            # print(f"硬件版本: {hw_version}")
            # print(f"软件版本: {sw_version}")
            # print(f"配置URL: {configuration_url}")
            # print(f"条目类型: {entry_type}")
            # print(f"禁用状态: {disabled_by}")
            # print(f"区域ID: {area_id}")
            # print(f"建议区域: {suggested_area}")
            # print(f"通过设备ID: {via_device_id}")
            # print(f"标识符: {identifiers}")
            # print(f"连接: {connections}")
            available_entities = []
            entity_infos = []
            for entity_id in entities:
                if entity_id.startswith('sensor.'):
                    continue
                entity = client.get_entity(entity_id=entity_id)
                friendly_name = entity.state.attributes['friendly_name'].replace(f"{device_name}", '').strip()
                entity_infos.append(entity)
                
                if entity.state.state=='unavailable':
                    continue
                available_entities.append(entity_id)
                # print(entity)
                
                # print(f"{device_name}|{friendly_name}")
            # print("-" * 50)
            if len(available_entities) == 0 and only_available:
                continue
            device_info['entities'] = entity_infos
            result.append(device_info)
    
    return result

if __name__ == "__main__":
    import os
    ha_url = os.getenv("HA_URL")
    token = os.getenv("HA_TOKEN")
    devices = get_ha_devices(ha_url, token, only_available=True)
    for device in devices:
        print(device['name'])