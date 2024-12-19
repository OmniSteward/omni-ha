from steward_utils import OmniTool, OmniAgent, Config, get_fn_args, JsonFixer
from openai import OpenAI
from homeassistant_api import Client as HomeAssistantClient
from .ha_utils import get_ha_devices

ha_system_prompt = """
你是一个Home Assistant控制专家，你的任务是根据用户的自然语言描述，回答用户的问题或控制Home Assistant中的智能设备。

你可以获取到所有可用设备的信息，包括:
- 设备名称
- 用户设定名称
- 型号
- 制造商
- 设备实体
- 建议区域

每个设备会有若干个实体，通过实体你可以知道设备的状态和属性，比如设备是否开启，设备是否支持某种操作，设备支持的属性有哪些。

下面我将给出所有可用设备及其实体的信息，请你仔细查看这些信息，因为用户需要的绝大部分的信息就在其中，选择回答用户的问题或者是进行设备控制。

"""

class InternalHomeAssistant(OmniTool):
    """
    用于实际控制Home Assistant设备的内部工具
    """
    name = 'internal_ha'
    description = '控制Home Assistant中的智能设备'
    parameters: dict = {
        "entity_id": {
            "type": "string",
            "description": "要控制的实体ID",
        },
        "service": {
            "type": "string", 
            "description": "要调用的服务，如turn_on, turn_off，toggle, select_option等",
        },
        "data": {
            "type": "object",
            "description": "服务调用的参数",
        }
    }
    
    config_items = [
        {'key': 'homeassistant.ha_url', 'default': None, 'required': True, 'map_to': 'ha_url'}, # Home Assistant的URL
        {'key': 'homeassistant.ha_token', 'default': None, 'required': True, 'map_to': 'ha_token'}, # Home Assistant的API令牌
    ]

    def __init__(self, config: Config):
        super().__init__(config)
        self.client = HomeAssistantClient(f'{self.ha_url}/api', self.ha_token)

    def __call__(self, entity_id: str, service: str, data: dict = None):
        if data is None:
            data = {}
        domain = entity_id.split('.')[0]
        try:
            # 获取特定域的服务对象
            domain_service = self.client.get_domain(domain)
            # 使用域服务对象直接调用服务
            if hasattr(domain_service, service):
                service_method = getattr(domain_service, service)
                result = service_method(entity_id=entity_id, **data)
                self.log('debug', f"结果: {result}")
                return f"成功控制设备 {entity_id}"
            else:
                self.log('error', f"控制设备失败: 服务 {service} 在域 {domain} 中不存在")
                return f"控制设备失败: 服务 {service} 在域 {domain} 中不存在"
        except Exception as e:
            self.log('error', f"控制设备失败: {str(e)}")
            return f"控制设备失败: {str(e)}"

class HomeAssistant(OmniAgent):
    """
    使用自然语言增强的智能家居控制
    """
    name = 'home_assistant'
    description = '使用自然语言检视或控制Home Assistant中的智能家居设备, 如果你认为某个设备是智能家居，可以用这个工具'
    parameters: dict = {
        "query": {
            "type": "string",
            "description": "用中文描述你想要检视或控制的Home Assistant中的智能家居设备",
        }
    }

    config_items = [
        {'key': 'homeassistant.ha_url', 'default': None, 'required': True, 'map_to': 'ha_url'}, # Home Assistant的URL
        {'key': 'homeassistant.ha_token', 'default': None, 'required': True, 'map_to': 'ha_token'}, # Home Assistant的API令牌
        {'key': 'homeassistant.ha_available_only', 'default': True, 'required': False, 'map_to': 'ha_available_only'}, # 是否只显示可用设备, 默认只显示可用设备
    ]

    agent_api_key_sources = ['homeassistant.openai_api_key','openai_api_key']
    agent_base_url_sources = ['homeassistant.openai_api_base','openai_api_base']
    agent_model_sources = ['homeassistant.model','model']

    def create_tools(self, config):
        return [InternalHomeAssistant(config)]

    def get_system_prompt(self):
        devices = get_ha_devices(self.ha_url, self.ha_token, only_available=self.ha_available_only)
        devices_info = []
        for device in devices:
            device_name = device['name']
            device_info = (
                f"设备: {device_name}\n"
                f"型号: {device.get('model', '未知')}\n"
                f"制造商: {device.get('manufacturer', '未知')}\n"
                f"位置: {device.get('suggested_area', '未知')}\n"
                f"可用实体:\n"
            )
            for entity in device['entities']:
                friendly_name = entity.state.attributes.get('friendly_name', '未知')
                friendly_name = friendly_name.replace(f"{device_name}", '').strip()
                entity_attrs = {k: v for k, v in entity.state.attributes.items()}
                entity_attrs['friendly_name'] = friendly_name
                name_map = {
                    "device_class": "type",
                    "friendly_name": "name",
                }
                # format entity_attrs
                for k, v in name_map.items():
                    if k in entity_attrs:
                        entity_attrs[v] = entity_attrs[k]
                        del entity_attrs[k]

                entity_attrs_str = ', '.join([f"{k}: {v}" for k, v in entity_attrs.items()])
                current_state = entity.state.state
                if current_state == 'on':
                    current_state = '开启'
                elif current_state == 'off':
                    current_state = '关闭'
                elif current_state == 'unknown':
                    current_state = '未知'
                device_info += f"entity_id: {entity.entity_id}, {entity_attrs_str}, 当前状态: {current_state}\n"
            devices_info.append(device_info)
        
        system_prompt = ha_system_prompt + "\n可用设备信息:\n" + "\n".join(devices_info)
        return system_prompt