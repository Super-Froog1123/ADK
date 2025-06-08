
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

def extract_google_sheet_url(tool_context: ToolContext) -> str:
    query = tool_context.input.parts[0].text
    if "docs.google.com/spreadsheets" in query:
        return query
    return ""

def return_html(option_code: str, tool_context: ToolContext) -> str:
    return f"""
<html>
<head><script src=\"https://cdn.jsdelivr.net/npm/echarts@5.4.2/dist/echarts.min.js\"></script></head>
<body>
<div id=\"main\" style=\"width: 600px;height:400px;\"></div>
<script>
  var chart = echarts.init(document.getElementById('main'));
  var option = {option_code};
  chart.setOption(option);
</script>
</body>
</html>
"""

agent_type_detector = Agent(
    model=MODEL,
    name='chart_type_agent',
    description='Analyze what chart type to use',
    instruction='You are an ECharts expert. Based on user request, output one of the following chart types: "bar", "line", "pie", "scatter", "wordcloud". Only output the type name.',
    generate_content_config=types.GenerateContentConfig(temperature=0.2),
    output_key='chart_type',
)

agent_data_fetcher = Agent(
    model=MODEL,
    name='sheet_data_agent',
    description='Extract Google Sheet link and provide simulated fetch logic',
    instruction='Extract the Google Sheet link from the input, and return JavaScript code that fetches CSV content using fetch(). Only return JavaScript code, no explanation.',
    tools=[extract_google_sheet_url],
    output_key='sheet_fetch_code',
    generate_content_config=types.GenerateContentConfig(temperature=0.2),
)

agent_code_writer = Agent(
    model=MODEL,
    name='echarts_code_agent',
    description='Generate ECharts option object',
    instruction='Based on the chart type and user intent, generate a full JavaScript object named "option" for ECharts. Do not wrap it in any HTML. Only return the JS object. Use the provided chart type: {chart_type}',
    generate_content_config=types.GenerateContentConfig(temperature=0.3),
    output_key='option_code',
)

agent_renderer = Agent(
    model=MODEL,
    name='html_output_agent',
    description='Returns complete HTML code for ECharts chart rendering',
    instruction='Use the generated ECharts option code to return a full HTML document that renders the chart. Include <script src=...> for echarts, and embed the "option" code properly.',
    tools=[return_html],
    generate_content_config=types.GenerateContentConfig(temperature=0.2),
)

echart_loop_agent = LoopAgent(
    name="echart_loop_agent",
    description="Loop agent to generate ECharts visualizations step-by-step.",
    sub_agents=[
        agent_type_detector,
        agent_data_fetcher,
        agent_code_writer,
        agent_renderer
    ]
)

root_agent = echart_loop_agent
