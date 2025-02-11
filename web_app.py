'''
-----------------------------------------------------------------------
File: app.py
Creation Time: Jan 30th 2024, 11:00 am
Author: Saurabh Zinjad
Developer Email: saurabhzinjad@gmail.com
Copyright (c) 2023-2024 Saurabh Zinjad. All rights reserved | https://github.com/Ztrimus
-----------------------------------------------------------------------
'''
import os
import json
import shutil
import streamlit as st


from zlm import AutoApplyModel
from zlm.utils.utils import display_pdf, download_pdf, read_file, read_json
from zlm.utils.metrics import jaccard_similarity, overlap_coefficient, cosine_similarity

st.set_page_config(
    page_title="Resume Generation!",
    page_icon="📑",
    menu_items={
        'About': 'https://github.com/Ztrimus/job-llm',
        'Report a bug': "https://github.com/Ztrimus/job-llm/issues",
    }
)

# st.markdown("<h1 style='text-align: center; color: grey;'>Get :green[Job Aligned] :orange[Killer] Resume :sunglasses:</h1>", unsafe_allow_html=True)
st.header("Get :green[Job Aligned] :orange[Personalized] Resume", divider='rainbow')
# st.subheader("Skip the writing, land the interview")

col_text, col_url,_,_ = st.columns(4)
with col_text:
    st.write("Job Description Text")
with col_url:
    is_url_button = st.toggle('Job URL', False)

url, text = "", ""
if is_url_button:
    url = st.text_input("Enter job posting URL:", placeholder="Enter job posting URL here...", label_visibility="collapsed")
else:
    text = st.text_area("Paste job description text:", max_chars=5500, height=200, placeholder="Paste job description text here...", label_visibility="collapsed")

file = st.file_uploader("Upload your resume or work related data (json, pdf)", type=["json", "pdf"])

col_1, col_2 = st.columns(2)
with col_1:
    provider = st.selectbox("Select LLM provider([OpenAI](https://openai.com/blog/openai-api), [Gemini Pro](https://ai.google.dev/)):", ["gemini-pro", "gpt-4"])
with col_2:
    api_key = st.text_input("Enter API key:", type="password")
    if api_key == "":
        api_key = None
st.markdown("---") 

# Buttons side-by-side with styling
col1, col2, col3 = st.columns(3)
with col1:
    get_resume_button = st.button("Get Resume", key="get_resume", type="primary")

with col2:
    get_cover_letter_button = st.button("Get Cover Letter", key="get_cover_letter", type="primary")

with col3:
    get_both = st.button("Resume + Cover letter", key="both", type="primary")
    if get_both:
        get_resume_button = True
        get_cover_letter_button = True

if get_resume_button or get_cover_letter_button:
    if file is None:
        st.toast(":red[Upload user's resume or work related data to get started]", icon="⚠️")
    
    if url == "" and text == "":
        st.toast(":red[Please enter a job posting URL or paste the job description to get started]", icon="⚠️") 
    
    if file is not None and (url != "" or text != ""):
        download_resume_path = os.path.join(os.path.dirname(__file__), "output")

        # st.write(f"download_resume_path: {download_resume_path}")

        llm_mapping = {'gpt-4':'openai', 'gemini-pro':'gemini'}

        resume_llm = AutoApplyModel(api_key=api_key, provider=llm_mapping[provider], downloads_dir=download_resume_path)
        
        # Save the uploaded file
        os.makedirs("uploads", exist_ok=True)
        file_path = os.path.abspath(os.path.join("uploads", file.name))
        with open(file_path, "wb") as f:
            f.write(file.getbuffer())
    
        # Extract user data
        with st.status("Extracting user data..."):
            user_data = resume_llm.user_data_extraction(file_path, is_st=True)
            st.write(user_data)

        shutil.rmtree(os.path.dirname(file_path))

        if user_data is None:
            st.error("User data not able process. Please upload a valid file or try again.")
            st.stop()

        # Extract job details
        with st.status("Extracting job details..."):
            if url != "":
                job_details, jd_path = resume_llm.job_details_extraction(url=url, is_st=True)
            elif text != "":
                job_details, jd_path = resume_llm.job_details_extraction(job_site_content=text, is_st=True)
            
            st.write(job_details)

        if job_details is None:
            st.error("Job details not able process. Please paste job description or try again.")
            st.stop()

        # Build Resume
        if get_resume_button:
            with st.status("Building resume..."):
                resume_path, resume_details = resume_llm.resume_builder(job_details, user_data, is_st=True)
                st.write("Outer resume_path: ", resume_path)
                st.write("Outer resume_details is None: ", resume_details is None)
            
            st.subheader("Generated Resume")
            pdf_data = read_file(resume_path, "rb")

            st.download_button(label="Download Resume ⬇",
                                data=pdf_data,
                                file_name=os.path.basename(resume_path),
                                on_click=download_pdf(resume_path),
                                key="download_pdf_button",
                                mime="application/pdf")
            
            display_pdf(resume_path)
            st.toast("Resume generated successfully!", icon="✅")
            # Calculate metrics
            st.subheader("Resume Metrics")
            for metric in ['overlap_coefficient', 'cosine_similarity']:
                user_personlization = globals()[metric](json.dumps(resume_details), json.dumps(user_data))
                job_alignment = globals()[metric](json.dumps(resume_details), json.dumps(job_details))
                job_match = globals()[metric](json.dumps(user_data), json.dumps(job_details))

                if metric == "overlap_coefficient":
                    title = "Overlap Coefficient"
                    help_text = "The overlap coefficient is a measure of the overlap between two sets, and is defined as the size of the intersection divided by the smaller of the size of the two sets."
                elif metric == "cosine_similarity":
                    title = "Cosine Similarity"
                    help_text = "The cosine similarity is a measure of the similarity between two non-zero vectors of an inner product space that measures the cosine of the angle between them."

                st.caption(f"## **:rainbow[{title}]**", help=help_text)
                col_m_1, col_m_2, col_m_3 = st.columns(3)
                col_m_1.metric(label=":green[User Personlization Score]", value=f"{user_personlization:.3f}", delta="[resume,master_data]", delta_color="off")
                col_m_2.metric(label=":blue[Job Alignment Score]", value=f"{job_alignment:.3f}", delta="[resume,JD]", delta_color="off")
                col_m_3.metric(label=":violet[Job Match Score]", value=f"{job_match:.3f}", delta="[master_data,JD]", delta_color="off")
            st.markdown("---")

        # Build Cover Letter
        if get_cover_letter_button:
            with st.status("Building cover letter..."):
                cv_details, cv_path = resume_llm.cover_letter_generator(job_details, user_data, is_st=True)
            st.subheader("Generated Cover Letter")
            cv_data = read_file(cv_path, "rb")
            st.download_button(label="Download ⬇",
                            data=cv_data,
                            file_name=os.path.basename(cv_path),
                            on_click=download_pdf(cv_path),
                            key="download_cv_button",
                            mime="application/pdf")
            st.markdown(cv_details, unsafe_allow_html=True)
            st.markdown("---")
            st.toast("cover letter generated successfully!", icon="✅")
        
        st.toast(f"Done", icon="👍🏻")
        st.success(f"Done", icon="👍🏻")
        st.balloons()
        
        refresh = st.button("Refresh")

        if refresh:
            st.caching.clear_cache()
            st.rerun()
