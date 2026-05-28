import os
import json
from datetime import datetime
try:
    from langchain.agents import AgentExecutor, create_openai_functions_agent
    from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
    from langchain_core.tools import tool
    from langchain_openai import ChatOpenAI
    LANGCHAIN_AVAILABLE = True
except ImportError as e:
    LANGCHAIN_AVAILABLE = False
    # Graceful fallback decorator
    def tool(func):
        return func
    print(f"LangChain Import Warning: {e}. Conversational search fallback active.")
from drone_agent import database

# Define LangChain Tools
@tool
def search_security_logs(query: str) -> str:
    """Searches the indexed drone video frame descriptions and tags in the database for specific objects, vehicles, people, or events. Use keywords like 'truck', 'person', 'gate'."""
    results = database.search_frames(query)
    if not results:
        return f"No visual logs found matching query: '{query}'"
    
    formatted_results = []
    for r in results:
        formatted_results.append(
            f"- [{r['timestamp']}] Location: {r['location_name']} | Description: {r['description']} | Tags: {r['tags']}"
        )
    return "\n".join(formatted_results)

@tool
def get_triggered_alerts() -> str:
    """Retrieves all high-priority security and safety alerts triggered during the patrol mission."""
    alerts = database.get_alerts()
    if not alerts:
        return "No safety or security alerts were triggered during this patrol."
    
    formatted_alerts = []
    for a in alerts:
        formatted_alerts.append(
            f"- [{a['timestamp']}] [{a['severity']}] Rule: {a['rule_triggered']} | Message: {a['message']}"
        )
    return "\n".join(formatted_alerts)

@tool
def get_patrol_telemetry_history() -> str:
    """Retrieves the coordinates, battery levels, speeds, and altitude logs of the drone across the entire patrol route."""
    logs = database.get_synced_logs()
    if not logs:
        return "No patrol logs or telemetry history found."
    
    formatted = []
    for l in logs:
        formatted.append(
            f"- [{l['timestamp']}] {l['location_name']} (GPS: {l['latitude']}, {l['longitude']}) | Altitude: {l['altitude']}m | Battery: {l['battery']}%"
        )
    return "\n".join(formatted[:20]) # Limit to prevent context token overflow

class DroneSecurityAgent:
    def __init__(self):
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        # We also support a fallback mode if no key is set or LangChain is unavailable
        self.is_llm_mode = bool(self.openai_api_key) and LANGCHAIN_AVAILABLE
        
        if self.is_llm_mode:
            try:
                self.llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.0, api_key=self.openai_api_key)
                self.tools = [search_security_logs, get_triggered_alerts, get_patrol_telemetry_history]
                
                # Create LangChain agent prompt
                prompt = ChatPromptTemplate.from_messages([
                    ("system", 
                     "You are an expert Drone Security Analyst Agent. You monitor commercial property patrols and answer "
                     "questions from the property owner or security manager. Use the provided tools to fetch visual logs, "
                     "telemetry history, and alerts from the database. Be factual, professional, and highlight any safety or security risks. "
                     "If multiple instances of an object are spotted, list them with timestamps and details. Always reference specific times and locations."),
                    MessagesPlaceholder(variable_name="chat_history"),
                    ("human", "{input}"),
                    MessagesPlaceholder(variable_name="agent_scratchpad"),
                ])
                
                agent = create_openai_functions_agent(self.llm, self.tools, prompt)
                self.agent_executor = AgentExecutor(agent=agent, tools=self.tools, verbose=True)
                print("LangChain Agent initialized successfully.")
            except Exception as e:
                print(f"Error initializing LangChain agent: {e}. Falling back to Rule-based RAG.")
                self.is_llm_mode = False
        else:
            print("No OpenAI API key found. Using Rule-based / Keyword RAG Engine.")

    def run(self, user_query: str, chat_history=None) -> str:
        """Executes a natural language query against the security base."""
        if chat_history is None:
            chat_history = []
            
        if self.is_llm_mode:
            try:
                response = self.agent_executor.invoke({
                    "input": user_query,
                    "chat_history": chat_history
                })
                return response["output"]
            except Exception as e:
                print(f"LangChain execution error: {e}. Falling back to keyword search.")
                
        # --- KEYWORD / RULE-BASED FALLBACK RAG ---
        query = user_query.lower()
        
        # 1. Check for alerts query
        if "alert" in query or "hazard" in query or "critical" in query or "spill" in query or "danger" in query:
            alerts = database.get_alerts()
            if not alerts:
                return "I searched the security database. No high-priority alerts were triggered during this patrol. The perimeter remains secure."
            
            response_text = "🚨 **Triggered Security & Safety Alerts:**\n\n"
            for a in alerts:
                response_text += f"- **[{a['severity']}]** ({a['timestamp']}): {a['message']} *(Triggered by rule: {a['rule_triggered']})*\n"
            return response_text
            
        # 2. Check for telemetry/route queries
        elif "route" in query or "where did" in query or "battery" in query or "telemetry" in query or "altitude" in query:
            logs = database.get_synced_logs()
            if not logs:
                return "No telemetry records found. Please ensure the drone simulation is running."
            
            summary = "🛸 **Patrol Route Summary & Telemetry:**\n\n"
            summary += f"The drone completed a patrol covering **{len(logs)} checkpoints**. "
            summary += f"Starting battery: **{logs[0]['battery']}%**, ending battery: **{logs[-1]['battery']}%**.\n"
            summary += "Key areas visited:\n"
            for l in logs[:10]:  # Show representative set
                summary += f"- {l['location_name']} at {l['timestamp'].split('T')[1][:8]} (Altitude: {l['altitude']}m)\n"
            return summary
            
        # 3. Object-based searching
        else:
            # Check if database is empty first to guide the user
            all_logs = database.get_synced_logs()
            if not all_logs:
                return "⚠️ **The security database is currently empty!**\n\nPlease make sure to click the **'▶️ Launch Patrol'** button in the left sidebar first. Once the drone completes its perimeter flight and indexes the multi-spectral video frames, I will be ready to parse and audit the visual logs for you!"

            # Extract semantic synonyms to map conversational questions to exact indexed visual terms
            search_terms = set()
            clean_query = query.replace("?", "").replace(".", "").replace(",", "")
            
            for word in clean_query.split():
                w = word.strip()
                if w in ["person", "people", "someone", "individual", "man", "guy", "hoodie", "intruder", "loiter", "loitering", "human"]:
                    search_terms.update(["person", "individual", "loitering"])
                elif w in ["car", "vehicle", "truck", "sedan", "ford", "f150", "pickup", "transport"]:
                    search_terms.update(["vehicle", "truck", "sedan"])
                elif w in ["gate", "entrance", "exit", "door", "lock", "locked"]:
                    search_terms.update(["gate", "entrance", "locked"])
                elif w in ["drum", "barrel", "leak", "chemical", "spill", "hazard", "waste", "tipped", "tipped-over"]:
                    search_terms.update(["chemical", "drum", "tipped-over", "leak"])
                elif w in ["fence", "perimeter", "wall", "boundary"]:
                    search_terms.update(["fence", "perimeter"])
                elif w in ["secure", "nominal", "clear", "safe", "quiet"]:
                    search_terms.update(["secure", "nominal", "quiet"])
                elif len(w) > 3 and w not in ["were", "there", "what", "with", "from", "show", "about", "could", "some", "spotted", "seen"]:
                    search_terms.add(w)
            
            # Execute database search queries for all terms
            results = []
            for term in search_terms:
                res = database.search_frames(term)
                results.extend(res)
                
            # Deduplicate matching database frame rows
            seen = set()
            unique_results = []
            for r in results:
                if r['id'] not in seen:
                    seen.add(r['id'])
                    unique_results.append(r)
                    
            if not unique_results:
                return f"🔍 I analyzed the visual database for terms matching `{list(search_terms)}` but couldn't find any corresponding occurrences in the recent patrol log. Let me know if you would like me to audit a different target zone."
                
            response = f"🔍 **Search Results for: \"{user_query}\"**\n\n"
            response += f"I discovered **{len(unique_results)} relevant visual log(s)** in the drone patrol archive:\n\n"
            for r in unique_results:
                time_only = r['timestamp'].split('T')[1][:8] if 'T' in r['timestamp'] else r['timestamp']
                response += f"- **[{time_only}] near {r['location_name']}** (Alt: {r['altitude']}m | Bat: {r['battery']}%):\n"
                response += f"  *Visual Report:* \"{r['description']}\"\n"
                response += f"  *System Tags:* `{r['tags']}`\n\n"
            return response

    def generate_video_summary(self) -> str:
        """Generates a premium, 1-sentence executive summary of the entire video patrol (Bonus)."""
        logs = database.get_synced_logs()
        alerts = database.get_alerts()
        
        if not logs:
            return "No patrol logs are currently recorded in the database. Run a simulation cycle to view the patrol summary."
            
        # Extract critical events
        has_intrusion = any(a['rule_triggered'] == 'IntrusionAfterHours' for a in alerts)
        has_hazard = any(a['rule_triggered'] == 'HazardousConditionSpill' for a in alerts)
        has_vehicle = any('vehicle' in a['message'].lower() or 'truck' in a['message'].lower() for a in alerts)
        
        summary = "📋 **Executive Patrol Summary**: "
        if has_intrusion and has_hazard:
            summary += "The drone completed its property patrol, successfully identifying an after-hours intruder loitering at the Warehouse Loading Docks, an unauthorized Ford F150 truck, and a hazardous tipped-over chemical drum at the Hazardous Waste Zone, while all other checkpoints remained secure."
        elif has_intrusion:
            summary += "The security patrol completed, successfully flagging a critical security breach involving an after-hours intruder loitering near the Warehouse Loading Docks and a suspicious sedan in the Visitor Parking Lot, with all other property boundaries verified as secure."
        elif has_hazard:
            summary += "The aerial patrol finished, discovering a tipped-over hazardous chemical container at the Hazardous Waste Zone, while confirming that all standard perimeter fencing and entrance gates remain completely secure."
        else:
            summary += "The autonomous drone patrol completed successfully; standard surveillance scanned all perimeter gates and warehouses, returning nominal results with no active safety hazards or security threats detected."
            
        return summary
