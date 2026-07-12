import streamlit as st
import json
import os
from openai import OpenAI

# ================= 1. 数据存储与初始化 =================
DATA_FILE = "students_db.json"

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# 初始化 Session State
if "db" not in st.session_state:
    st.session_state.db = load_data()
if "current_student" not in st.session_state:
    st.session_state.current_student = None

# ================= 2. 大模型交互逻辑 =================
def call_llm(api_key, system_prompt, user_prompt):
    # 这里默认使用 OpenAI 官方接口，如果你用国内模型（如通义千问/月之暗面/DeepSeek），
    # 可以在这里加上 base_url="他们的接口地址"
  def call_llm(api_key, system_prompt, user_prompt):
    # 配置 DeepSeek 的接口地址
    client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com") 
    try:
        response = client.chat.completions.create(
            model="deepseek-chat", # 使用 DeepSeek 模型
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.7
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"API请求出错，请检查API Key或网络: {e}"

def analyze_initial_doc(api_key, doc_text):
    system_prompt = "你是一个专业的线上教育助教督导。请分析学前沟通记录，总结学生的学习基础、性格特点，并给出第一次与家长沟通的策略和破冰话题。请以JSON格式输出，包含字段：'mastery' (掌握情况), 'strategy' (家长沟通策略), 'next_topics' (下次沟通话题)。"
    user_prompt = f"学前沟通记录如下：\n{doc_text}\n请分析并输出。"
    return call_llm(api_key, system_prompt, user_prompt)

def update_student_profile(api_key, profile, new_feedback):
    system_prompt = "你是一个专业的线上教育助教督导。根据学生目前的档案和助教最新输入的沟通反馈，更新该学生的掌握情况，并提供给家长解决问题的方向，以及规划下一次沟通的话题。请以清晰的Markdown格式输出：1. 最新掌握情况更新 2. 给家长的解决问题方向 3. 下次沟通推荐话题。"
    user_prompt = f"【当前档案】\n掌握情况：{profile.get('mastery', '')}\n\n【本次沟通反馈】\n{new_feedback}\n\n请进行迭代更新并输出指导建议。"
    return call_llm(api_key, system_prompt, user_prompt)

# ================= 3. 页面 UI 布局 =================
st.set_page_config(page_title="助教智能沟通助手", layout="wide")
st.title("🤖 交互式助教沟通助手")

with st.sidebar:
    st.header("⚙️ 基础设置")
    # 请把里面的 sk-... 换成你真实申请到的那一长串 Key
    api_key = st.secrets["API_KEY"]
    st.caption("没有Key？可以去阿里云(百炼)或DeepSeek官网免费申请一个。")
    
    st.divider()
    st.header("🧑‍🎓 学生管理")
    student_name = st.text_input("请输入学生姓名：", placeholder="例如：李小明")
    
    if st.button("确认选择 / 切换学生"):
        if student_name:
            st.session_state.current_student = student_name
            if student_name not in st.session_state.db:
                st.session_state.db[student_name] = {
                    "mastery": "暂无记录",
                    "strategy": "暂无记录",
                    "next_topics": "暂无记录",
                    "history": []
                }
                save_data(st.session_state.db)
                st.success(f"已为您新建学生档案：{student_name}")
            else:
                st.success(f"已加载学生档案：{student_name}")

if st.session_state.current_student:
    student = st.session_state.current_student
    profile = st.session_state.db[student]
    
    st.subheader(f"📖 当前学生：【{student}】档案卡")
    
    col1, col2 = st.columns(2)
    with col1:
        st.info("🧠 **当前掌握情况**")
        st.write(profile["mastery"])
    with col2:
        st.success("🎯 **下次沟通话题/策略**")
        st.write(profile["next_topics"])
        
    st.divider()
    
    st.subheader("📁 1. 上传学前沟通记录 (初始化/重置档案)")
    uploaded_file = st.file_uploader("上传沟通记录(仅支持TXT文本文件)", type=["txt"])
    if uploaded_file is not None and api_key:
        if st.button("解析文档并生成沟通策略"):
           with st.spinner("正在分析文档..."):
                # 升级：双重解码保障（先试 utf-8，不行就用 gbk）
                try:
                    doc_content = uploaded_file.getvalue().decode("utf-8")
                except UnicodeDecodeError:
                    doc_content = uploaded_file.getvalue().decode("gbk")
                    
                profile["history"].append({"type": "document_upload", "content": doc_content})
                
                # 剩下的保持你原本的优秀逻辑
                ai_result = analyze_initial_doc(api_key, doc_content)
                try:
                    result_dict = json.loads(ai_result)
                    profile["mastery"] = result_dict.get("mastery", "")
                    profile["strategy"] = result_dict.get("strategy", "")
                    profile["next_topics"] = result_dict.get("next_topics", "")
                except:
                    profile["mastery"] = ai_result
                    
                save_data(st.session_state.db)
                st.success("文档解析完成！")
                st.rerun()

    st.divider()
    
    st.subheader("💬 2. 补充最新沟通反馈 (迭代更新)")
    st.write("与家长沟通后，将情况输入在下方，助手将自动更新档案并制定下一次沟通计划。")
    
    new_feedback = st.chat_input("输入本次沟通情况...")
    if new_feedback:
        if not api_key:
            st.error("请先在左侧边栏输入 API Key")
        else:
            with st.chat_message("user"):
                st.write(new_feedback)
            
            with st.chat_message("assistant"):
                with st.spinner("正在思考策略并更新档案..."):
                    ai_reply = update_student_profile(api_key, profile, new_feedback)
                    st.markdown(ai_reply)
                    
                    profile["history"].append({
                        "type": "feedback", 
                        "content": new_feedback, 
                        "ai_response": ai_reply
                    })
                    profile["next_topics"] = ai_reply
                    save_data(st.session_state.db)
else:
    st.info("👈 请先在左侧边栏输入 API Key 并选择一个学生姓名开启工作。")
