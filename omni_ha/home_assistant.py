from steward_utils import OmniTool, Config, get_fn_args, JsonFixer
from openai import OpenAI
from homeassistant_api import Client as HomeAssistantClient
from .ha_utils import get_ha_devices

ha_system_prompt = """
你是一个Home Assistant控制专家，你的任务是根据用户的自然语言描述，控制Home Assistant中的智能设备。

你可以获取到所有可用设备的信息，包括:
- 设备名称(name)
- 用户设定名称(name_by_user)
- 型号(model)
- 制造商(manufacturer)
- 设备实体(entities)
- 建议区域(suggested_area)

每个设备实体都有其状态(state)和属性(attributes)。

请根据用户的描述，选择合适的设备和操作方式。
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

    def __init__(self, config: Config):
        super().__init__(config)
        self.client = HomeAssistantClient(f'{config.ha_url}/api', config.ha_token)

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
                print(f"DEBUG - 结果: {result}")
                return f"成功控制设备 {entity_id}"
            else:
                return f"控制设备失败: 服务 {service} 在域 {domain} 中不存在"
        except Exception as e:
            return f"控制设备失败: {str(e)}"

class HomeAssistant(OmniTool):
    """
    使用自然语言增强的智能家居控制
    """
    name = 'home_assistant'
    description = '使用自然语言控制Home Assistant中的智能家居设备, 如果你认为某个设备是智能家居，可以用这个工具来控制它'
    parameters: dict = {
        "query": {
            "type": "string",
            "description": "用自然语言描述你想要执行的Home Assistant中的智能家居设备",
        }
    }
    config_items = [
        {'key': 'openai_api_key', 'default': None, 'required': True},
        {'key': 'openai_api_base', 'default': None, 'required': True},
        {'key': 'model', 'default': None, 'required': True},
        {'key': 'ha_url', 'default': None, 'required': True}, # Home Assistant的URL
        {'key': 'ha_token', 'default': None, 'required': True}, # Home Assistant的API令牌
        {'key': 'ha_available_only', 'default': True, 'required': False}, # 是否只显示可用设备, 默认只显示可用设备
    ]

    def __init__(self, config: Config):
        super().__init__(config)
        self.client = OpenAI(
            api_key=self.openai_api_key,
            base_url=self.openai_api_base,
        )
        self.internal_ha = InternalHomeAssistant(config)
        

    def construct_system_prompt(self, devices):
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
                device_info += f"entity_id: {entity.entity_id}, {entity_attrs_str} (当前状态: {entity.state.state})\n"
            devices_info.append(device_info)
        
        system_prompt = ha_system_prompt + "\n可用设备信息:\n" + "\n".join(devices_info)
        return system_prompt

    def __call__(self, query):
        devices = get_ha_devices(self.ha_url, self.ha_token, only_available=self.ha_available_only)
        system_prompt = self.construct_system_prompt(devices)
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": query},
            ],
            tools=[self.internal_ha.json()],
        )
        
        message = response.choices[0].message.model_dump()
        print(f"DEBUG - AI响应: {message}")
        content = message['content']
        if len(content) != 0:
            print(f"DEBUG - AI响应: {content}")
        
        tool_calls = message['tool_calls']
        if tool_calls is None:
            return '控制失败: AI没有给出具体操作指令'
            
        results = []
        for tool_call in tool_calls:
            fn_call = tool_call['function']
            fn_name = fn_call['name']
            if fn_name != 'internal_ha':
                continue
            fn_args = get_fn_args(fn_call)
            if fn_args is None:
                print(f"DEBUG - 解析参数失败: {fn_call['arguments']}，尝试修复")
                json_fixer = JsonFixer(self.openai_api_key, self.openai_api_base, self.model)
                fn_args = json_fixer.fix_json(fn_call['arguments'])
                print(f"DEBUG - 修复后的参数: {fn_args}, type: {type(fn_args)}")

            print(f"DEBUG - 调用参数: {fn_args}")
                
            result = self.internal_ha(**fn_args)
            results.append(result)
            
        return '\n'.join(results) if results else '没有执行任何操作'
