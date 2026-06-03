"""
智扫通机器人智能客服 - Streamlit 前端入口
支持对话历史持久化到 SQLite 数据库
"""
import uuid

import streamlit as st
from agent.react_agent import ReactAgent
from utils.database import save_message, get_conversation_messages, create_conversation, get_conversation

# 页面配置
st.set_page_config(page_title="智扫通机器人智能客服", page_icon="🤖")
st.title("智扫通机器人智能客服")
st.divider()

# MODIFIED: 初始化 session_id （用于持久化）
if "session_id" not in st.session_state:
    st.session_state["session_id"] = str(uuid.uuid4())[:8]
    # 在数据库中创建会话记录
    create_conversation(st.session_state["session_id"], "新对话")

if "agent" not in st.session_state:
    st.session_state["agent"] = ReactAgent()

# MODIFIED: 从数据库加载历史消息
if "message" not in st.session_state:
    st.session_state["message"] = get_conversation_messages(st.session_state["session_id"])

# 侧边栏 - 会话管理
with st.sidebar:
    st.header("会话管理")
    if st.button("新建对话", use_container_width=True):
        st.session_state["session_id"] = str(uuid.uuid4())[:8]
        create_conversation(st.session_state["session_id"], "新对话")
        st.session_state["message"] = []
        st.rerun()

    st.divider()
    st.caption(f"当前会话: {st.session_state['session_id']}")

# 渲染对话历史
for message in st.session_state["message"]:
    st.chat_message(message["role"]).write(message["content"])

# 用户输入
prompt = st.chat_input("请输入您关于扫地机器人的问题...")

if prompt:
    # 显示用户消息
    st.chat_message("user").write(prompt)
    st.session_state["message"].append({"role": "user", "content": prompt})

    # 保存用户消息到数据库
    save_message(st.session_state["session_id"], "user", prompt)

    # 获取 AI 回复
    response_message = []
    with st.spinner("智能客服思考中..."):
        res_stream = st.session_state["agent"].execute_stream(prompt)

        # 缓存流式数据再输出
        def cache_and_yield(generator, cache_list):
            for chunk in generator:
                cache_list.append(chunk)
                yield chunk

        st.chat_message("assistant").write_stream(
            cache_and_yield(res_stream, response_message)
        )

    if response_message:
        full_response = "".join(response_message)
        st.session_state["message"].append({"role": "assistant", "content": full_response})
        # MODIFIED: 保存 AI 回复到数据库
        save_message(st.session_state["session_id"], "assistant", full_response)
    st.rerun()
