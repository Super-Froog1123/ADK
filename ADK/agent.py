import random
from google.adk.agents import Agent
from google.adk.agents.loop_agent import LoopAgent
from google.adk.artifacts import InMemoryArtifactService
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.tools.tool_context import ToolContext
from google.genai import types
from typing import Any

MODEL = "gemini-2.0-flash"

# 工具函数：提取 Google Sheet 链接
def extract_google_sheet_url(tool_context: ToolContext) -> str:
    query = tool_context.input.parts[0].text
    if "docs.google.com/spreadsheets" in query:
        return query
    return ""

# 工具函数：将 option 转换为完整 HTML 页面
def return_html(option_code: str, tool_context: ToolContext) -> str:
    return f"""
<html>
<head><script src="https://cdn.jsdelivr.net/npm/echarts@5.4.2/dist/echarts.min.js"></script></head>
<body>
<div id="main" style="width: 600px;height:400px;"></div>
<script>
  var chart = echarts.init(document.getElementById('main'));
  var option = {option_code};
  chart.setOption(option);
</script>
</body>
</html>
"""

# 终止逻辑：根据用户输入判断是否退出循环
def exit_loop(tool_context: ToolContext) -> bool:
    user_input = tool_context.input.parts[0].text.lower()
    return any(word in user_input for word in ["no", "exit", "quit", "不", "结束", "停止"])

# 新增：询问用户 Sheet 链接 Agent
ask_sheet_link_agent = Agent(
    model=MODEL,
    name="ask_sheet_link_agent",
    description="Ask user for a Google Sheet link",
    instruction="Ask the user to paste a Google Sheet link that contains the data they want to visualize. Be friendly and concise.",
    generate_content_config=types.GenerateContentConfig(temperature=0.2),
)

# 图表类型判断 Agent
agent_type_detector = Agent(
    model=MODEL,
    name='chart_type_agent',
    description='Analyze what chart type to use',
    instruction='You are an ECharts expert. Based on user request, output one of the following chart types: "bar", "line", "pie", "scatter", "wordcloud". Only output the type name.',
    generate_content_config=types.GenerateContentConfig(temperature=0.2),
    output_key='chart_type',
)

# 数据抓取 Agent
agent_data_fetcher = Agent(
    model=MODEL,
    name='sheet_data_agent',
    description='Extract Google Sheet link and provide simulated fetch logic',
    instruction='Extract the Google Sheet link from the input, and return JavaScript code that fetches CSV content using fetch(). Only return JavaScript code, no explanation.',
    tools=[extract_google_sheet_url],
    output_key='sheet_fetch_code',
    generate_content_config=types.GenerateContentConfig(temperature=0.2),
)

# ECharts 配置生成 Agent
agent_code_writer = Agent(
    model=MODEL,
    name='echarts_code_agent',
    description='Generate ECharts option object',
    instruction='Based on the chart type and user intent, generate a full JavaScript object named "option" for ECharts. Do not wrap it in any HTML. Only return the JS object. Use the provided chart type: {chart_type}',
    generate_content_config=types.GenerateContentConfig(temperature=0.3),
    output_key='option_code',
)

# 渲染 HTML 输出 Agent
agent_renderer = Agent(
    model=MODEL,
    name='html_output_agent',
    description='Returns complete HTML code for ECharts chart rendering',
    instruction='Use the generated ECharts option code to return a full HTML document that renders the chart. Include <script src=...> for echarts, and embed the "option" code properly.',
    tools=[return_html],
    generate_content_config=types.GenerateContentConfig(temperature=0.2),
)

# 主循环 Agent，支持自动继续或终止
echart_loop_agent = LoopAgent(
    name="echart_loop_agent",
    description="Loop agent to generate ECharts visualizations step-by-step.",
    sub_agents=[
        ask_sheet_link_agent,  # 第一步：询问用户输入 Google Sheet 链接
        agent_type_detector,
        agent_data_fetcher,
        agent_code_writer,
        agent_renderer
    ],
    should_continue=exit_loop,
    after_each=lambda context: context.reply("是否要继续生成另一个图表？（输入“no”或“结束”来停止）")
)

# 根 Agent
root_agent = echart_loop_agent
