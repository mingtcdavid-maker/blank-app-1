import streamlit as st

def compiledata():
    st.title("HDB Ops Survey Report Generator")
    with st.form("registration_form"):
        block_no = st.text_input("Block Number")
        street_name = st.text_input("Street Name")
        nearest_hydrant = st.text_input("Nearest Hydrant Number. i.e. DPH12345")
        number_breaching = st.number_input("Number of Breaching Inlets")
        pic_best_appliance = st.file_uploader("Upload image of best appliance placement", accept_multiple_files=True)
        pic_nearest_hydrant = st.file_uploader("Upload Photo of nearest hydrant", accept_multiple_files=True)
        pic_nearest_breaching = st.file_uploader("Upload photo of nearest breaching inlet", accept_multiple_files=True)

        submit = st.form_submit_button(label="Generate Report")

    if submit:
        st.success("Generation in progress, wait 30 seconds.")
        st.session_state.status = True
        data = {
            "block_no": block_no,
            "street_name": street_name,
            "nearest_hydrant": nearest_hydrant,
            "number_breaching": number_breaching,
            "pic_best_appliance": pic_best_appliance,
            "pic_nearest_hydrant": pic_nearest_hydrant,
            "pic_nearest_breaching": pic_nearest_breaching,
        }
        st.session_state.data = data
        return data