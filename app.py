import streamlit as st
import json
import os
import random

DATA_FILE = "data.json"

DEFAULT_COLORS = [
    "#FF6B6B", "#4ECDC4", "#45B7D1", "#96CEB4", "#FFEAA7",
    "#DDA0DD", "#98D8C8", "#F7DC6F", "#BB8FCE", "#85C1E9",
    "#F8B500", "#00CED1", "#FF69B4", "#32CD32", "#FF8C00"
]

def load_env():
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    if os.path.exists(env_path):
        with open(env_path, "r") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    os.environ[key] = value.strip()

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

def get_next_color(data):
    used = {v.get("color", "") for v in data.get("categories", {}).values()}
    for color in DEFAULT_COLORS:
        if color not in used:
            return color
    return f"#{random.randint(0, 0xFFFFFF):06x}"

def get_category_index(data, cat_name):
    if "indices" not in data:
        data["indices"] = {}
    if cat_name not in data["indices"]:
        data["indices"][cat_name] = 0
    return data["indices"][cat_name]

def set_category_index(data, cat_name, index):
    if "indices" not in data:
        data["indices"] = {}
    data["indices"][cat_name] = index
    save_data(data)

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
            activities = valid_categories[cat_name]["activities"]
            mode = valid_categories[cat_name].get("mode", "random")
            
            if mode == "order":
                idx = get_category_index(data, cat_name)
                selected = []
                for i in range(count):
                    if idx >= len(activities):
                        idx = 0
                    selected.append(activities[idx])
                    idx += 1
                set_category_index(data, cat_name, idx)
            else:
                selected = random.sample(activities, count)
            
            recommendations.extend([(cat_name, act) for act in selected])
    
    return recommendations[:total_activities]

def check_password():
    load_env()
    correct_password = os.environ.get("APP_PASSWORD", "")
    
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    
    if not st.session_state.authenticated:
        st.title("🔒 Daily Planner - Login")
        password = st.text_input("Enter Password", type="password")
        if st.button("Login"):
            if password == correct_password:
                st.session_state.authenticated = True
                st.rerun()
            else:
                st.error("Incorrect password")
        return False
    return True

st.set_page_config(page_title="Daily Planner", layout="wide")

if not check_password():
    st.stop()

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
        data["categories"][new_name] = {
            "percent": 0, 
            "activities": [], 
            "color": get_next_color(data),
            "mode": "random"
        }
        save_data(data)
        st.rerun()
    
    for cat_name, cat_data in list(data["categories"].items()):
        color = cat_data.get("color", "#808080")
        with st.expander(f"{cat_name}", expanded=True):
            new_name = st.text_input("Name", value=cat_name, key=f"name_{cat_name}")
            if new_name != cat_name and new_name not in data["categories"]:
                data["categories"][new_name] = data["categories"].pop(cat_name)
                save_data(data)
                st.rerun()
            
            new_color = st.color_picker("Color", value=color, key=f"color_{cat_name}")
            if new_color != color:
                data["categories"][cat_name]["color"] = new_color
                save_data(data)
                st.rerun()
            
            mode = st.selectbox(
                "Selection Mode",
                ["random", "order"],
                index=0 if cat_data.get("mode", "random") == "random" else 1,
                key=f"mode_{cat_name}",
                help="Random: picks randomly each time. Order: goes through activities sequentially."
            )
            if mode != cat_data.get("mode", "random"):
                data["categories"][cat_name]["mode"] = mode
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
                if "indices" in data and cat_name in data["indices"]:
                    del data["indices"][cat_name]
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
            color = data["categories"][cat].get("color", "#808080")
            mode = data["categories"][cat].get("mode", "random")
            st.markdown(
                f"<div style='background-color: {color}22; border-left: 4px solid {color}; "
                f"padding: 8px 12px; margin: 4px 0; border-radius: 4px;'>"
                f"<strong style='color: {color};'>{cat}</strong> "
                f"<span style='color: #888; font-size: 0.85em;'>({mode})</span>: {act}"
                f"</div>",
                unsafe_allow_html=True
            )
    else:
        st.warning("No categories with percent > 0 or no activities available.")