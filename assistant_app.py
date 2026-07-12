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
    client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com") 
    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
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
    # 【升级版提示词】强制要求详细展开，给出话术和步骤
    system_prompt = """你是一位拥有10年经验的顶尖线上教育督导，精通家校沟通与学生心理学。请深度分析学前沟通记录，并给出极具实操性的沟通方案。
    请必须以纯JSON格式输出（不要加 ```json 代码块等额外字符），包含以下三个字段，且内容要求非常详实：
    
    1. 'mastery' (掌握情况及性格画像)：深度剖析学生的学习基础、习惯痛点、厌学原因以及核心性格特征。
    2. 'strategy' (家长沟通策略)：提供超详细的解决方案，必须包含：
       - 核心沟通目标（本次沟通要解决的首要问题）
       - 分步骤的沟通框架（第一步聊什么，第二步聊什么，如何引导）
       - 具体话术示范（例如：针对该学生的特殊情况，助教第一句话具体该怎么发微信或打电话）
    3. 'next_topics' (下次沟通话题)：给出2-3个具体的破冰或跟进话题，并说明为什么用这个话题能吸引学生或家长。"""
    
    user_prompt = f"学前沟通记录如下：\n{doc_text}\n请分析并输出。"
    return call_llm(api_key, system_prompt, user_prompt)

def update_student_profile(api_key, profile, new_feedback):
    # 【升级版提示词】强制要求复盘并给出针对性极强的下一步建议
    system_prompt = """你是一位拥有10年经验的顶尖线上教育督导。请根据学生目前的档案和助教刚刚提交的最新沟通反馈，进行深度复盘，并制定下一步行动计划。
    请以清晰的 Markdown 格式输出，内容要求丰富且具有极强的指导性：
    
    ### 1. 📊 学生状态刷新
    综合旧档案与新反馈，分析学生目前的心态变化和学习进展。
    
    ### 2. 💡 给家长的实操解决方案
    不要讲空话，给出具体的指导建议。例如：如何化解学生借口、如何建立奖惩机制、家长在家里具体应该配合做哪三件事。
    
    ### 3. 🎯 助教下一步跟进剧本
    为助教规划下一次的沟通策略，包含明确的跟进时间点建议，以及一段可以直接复制使用的沟通话术示范。"""
    
    user_prompt = f"【当前档案】\n掌握情况：{profile.get('mastery', '')}\n\n【本次沟通反馈】\n{new_feedback}\n\n请进行迭代更新并输出详实的指导建议。"
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
    
    # 1. 自动读取后台数据库里已经存了哪些学生
    existing_students = list(st.session_state.db.keys())
    
    # 2. 增加一个下拉菜单，展示已有档案
    selected_student = st.selectbox("📂 调取已有档案：", ["(请选择...)"] + existing_students)
    
    # 3. 保留新建学生的输入框
    new_student = st.text_input("🆕 或新建学生档案：", placeholder="输入新学生姓名")
    
    if st.button("确认选择 / 切换学生"):
        # 逻辑：优先看有没有输入新名字，没输入新名字就用下拉菜单选的名字
        final_student_name = new_student if new_student else selected_student
        
        if final_student_name and final_student_name != "(请选择...)":
            st.session_state.current_student = final_student_name
            
            # 检查是不是全新的人
            if final_student_name not in st.session_state.db:
                st.session_state.db[final_student_name] = {
                    "mastery": "暂无记录",
                    "strategy": "暂无记录",
                    "next_topics": "暂无记录",
                    "history": []
                }
                save_data(st.session_state.db)
                st.success(f"✨ 已为您新建档案：{final_student_name}")
            else:
                st.success(f"📚 已成功提取【{final_student_name}】的历史档案！")
        else:
            st.warning("请先输入或选择一个学生姓名！")
    
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
        st.write(profile.get("mastery") or "暂无记录，请先上传并解析文档。")
    with col2:
        st.success("🎯 **下次沟通话题/策略**")
        st.write(profile.get("next_topics") or "暂无记录，请先上传并解析文档。")
        
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
