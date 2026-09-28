import streamlit as st
import json
import os
import random

DATA_FILE = "data.json"

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {"categories": {}}

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)

def get_total_percent(data):
    return sum(v.get("percent", 0) for v in data.get("categories", {}).values())

def recommend_activities(data, total_activities):
    categories = data.get("categories", {})
    valid_categories = {k: v for k, v in categories.items() if v.get("percent", 0) > 0}
    
    if not valid_categories:
        return []
    
    total_percent = sum(v["percent"] for v in valid_categories.values())
    if total_percent != 100:
        return []
    
    recommendations = []
    counts = {}
    
    for cat_name, cat_data in valid_categories.items():
        count = int(round(cat_data["percent"] / 100 * total_activities))
        counts[cat_name] = min(count, len(cat_data.get("activities", [])))
    
    total_allocated = sum(counts.values())
    remaining = total_activities - total_allocated
    
    if remaining > 0:
        for cat_name in valid_categories:
            if remaining <= 0:
                break
            available = len(valid_categories[cat_name].get("activities", [])) - counts[cat_name]
            if available > 0:
                take = min(remaining, available)
                counts[cat_name] += take
                remaining -= take
    
    for cat_name, count in counts.items():
        if count > 0:
            selected = random.sample(valid_categories[cat_name]["activities"], count)
            recommendations.extend([(cat_name, act) for act in selected])
    
    return recommendations[:total_activities]

st.set_page_config(page_title="Daily Planner", layout="wide")
st.title("Daily Planner")

data = load_data()
total_percent = get_total_percent(data)

with st.sidebar:
    st.header("Categories")
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Total %", f"{total_percent}%")
    with col2:
        if total_percent == 100:
            st.success("✓ Valid")
        else:
            st.error(f"✗ Must be 100%")
    
    if st.button("Add Category"):
        new_name = f"Category {len(data['categories']) + 1}"
        data["categories"][new_name] = {"percent": 0, "activities": []}
        save_data(data)
        st.rerun()
    
    for cat_name, cat_data in list(data["categories"].items()):
        with st.expander(cat_name, expanded=True):
            new_name = st.text_input("Name", value=cat_name, key=f"name_{cat_name}")
            if new_name != cat_name and new_name not in data["categories"]:
                data["categories"][new_name] = data["categories"].pop(cat_name)
                save_data(data)
                st.rerun()
            
            max_percent = 100 - (total_percent - cat_data["percent"])
            percent = st.number_input(
                "Percent (%)", 
                min_value=0, 
                max_value=max_percent, 
                value=cat_data["percent"], 
                key=f"percent_{cat_name}"
            )
            if percent != cat_data["percent"]:
                data["categories"][cat_name]["percent"] = percent
                save_data(data)
                st.rerun()
            
            st.subheader("Activities")
            for i, activity in enumerate(cat_data["activities"]):
                col1, col2 = st.columns([4, 1])
                with col1:
                    new_act = st.text_input(f"Activity {i+1}", value=activity, key=f"act_{cat_name}_{i}")
                    if new_act != activity:
                        data["categories"][cat_name]["activities"][i] = new_act
                        save_data(data)
                        st.rerun()
                with col2:
                    if st.button("Delete", key=f"del_act_{cat_name}_{i}"):
                        data["categories"][cat_name]["activities"].pop(i)
                        save_data(data)
                        st.rerun()
            
            new_activity = st.text_input("Add Activity", key=f"new_act_{cat_name}")
            if st.button("Add", key=f"add_act_{cat_name}") and new_activity:
                data["categories"][cat_name]["activities"].append(new_activity)
                save_data(data)
                st.rerun()
            
            if st.button("Delete Category", key=f"del_cat_{cat_name}"):
                del data["categories"][cat_name]
                save_data(data)
                st.rerun()

st.header("Recommend Activities")
total_activities = st.number_input("Total Activities Wanted", min_value=1, max_value=100, value=5)

if total_percent != 100:
    st.warning(f"Total percentage is {total_percent}%. It must equal 100% to recommend activities.")

if st.button("Recommend Activities", type="primary", disabled=total_percent != 100):
    recommendations = recommend_activities(data, total_activities)
    if recommendations:
        st.success(f"Recommended {len(recommendations)} activities:")
        for cat, act in recommendations:
            st.write(f"**{cat}**: {act}")
    else:
        st.warning("No categories with percent > 0 or no activities available.")