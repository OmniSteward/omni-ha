import os
from omni_ha.home_assistant import HomeAssistant
from steward_utils import load_config_from_json

if __name__ == "__main__":
    config = load_config_from_json(os.getenv("JSON_PATH")) # 从json文件中加载配置
    config.model = os.getenv("MODEL") # 设置模型
    config.ha_url = os.getenv("HA_URL") # 设置Home Assistant的URL
    config.ha_token = os.getenv("HA_TOKEN") # 设置Home Assistant的API令牌
    
    print(config)
    ha = HomeAssistant(config)
    ha("打开空气净化器指示灯")
    ha("关闭空气净化器")
    # ha("空气净化器调到最爱")