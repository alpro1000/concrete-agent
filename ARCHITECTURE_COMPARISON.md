# Beads System - Architecture Comparison

## Before: Hardcoded Agent System ❌

```
┌─────────────────────────────────────────────────┐
│           Orchestrator (orchestrator.py)        │
│                                                 │
│  async def _get_agent(agent_name):              │
│    if agent_name == 'tzd':  ❌ HARDCODED        │
│      from agents.tzd_reader import TZDReader    │
│      return TZDReader()                         │
│    elif agent_name == 'concrete':               │
│      from agents.concrete import ConcreteAgent  │
│      return ConcreteAgent()                     │
│    elif agent_name == 'material':               │
│      ...more hardcoded agents...                │
└─────────────────────────────────────────────────┘
           ↓ ↓ ↓ ↓ ↓
   ┌───────┐ ┌────────┐ ┌──────────┐
   │  TZD  │ │Concrete│ │ Material │
   │Reader │ │ Agent  │ │  Agent   │
   └───────┘ └────────┘ └──────────┘

Problems:
❌ Orchestrator imports specific agents
❌ Adding agent requires code change in orchestrator
❌ Tight coupling between core and agents
❌ Can't add agents without modifying core files
```

## After: Beads System (Dynamic Discovery) ✅

```
┌─────────────────────────────────────────────────┐
│           Orchestrator (orchestrator.py)        │
│                                                 │
│  def discover_agents(agents_dir):               │
│    ✅ Scans directory for agent.py files        │
│    ✅ Imports modules dynamically               │
│    ✅ Finds classes with BaseAgent interface    │
│    ✅ No hardcoded agent names!                 │
│                                                 │
│  def get_agent_for_type(file_type):             │
│    ✅ Matches file_type to agent.supported_types│
│    ✅ Returns appropriate agent instance        │
└─────────────────────────────────────────────────┘
           ↓ (automatic discovery)
     ┌─────────────────────┐
     │   app/agents/       │
     │   └── */agent.py    │
     └─────────────────────┘
           ↓ ↓ ↓
   ┌───────────┐
   │ BaseAgent │  ← Abstract Interface
   └───────────┘
         ↑ ↑ ↑
   ┌─────┴─────┴──────┐
   │ TZDReaderAgent   │
   │                  │
   │ name = "tzd"     │
   │ supported_types  │
   │   = ["pdf",      │
   │      "technical"]│
   │ analyze(path)    │
   └──────────────────┘

Benefits:
✅ Zero hardcoded agent references
✅ Add agents by just creating folder
✅ Core is completely agent-agnostic
✅ Loose coupling via interface
✅ Plug & play architecture
```

## Flow Comparison

### Before (Hardcoded):
```
1. File uploaded → "technical.pdf"
2. Orchestrator: if file_type == 'technical':
3.    agent = self._get_agent('tzd')  ❌ Hardcoded name
4.    if agent_name == 'tzd':          ❌ Hardcoded check
5.        from agents.tzd_reader ...  ❌ Hardcoded import
6.        return TZDReader()
7. Agent processes file
```

### After (Beads System):
```
1. File uploaded → "technical.pdf"
2. Orchestrator.detect_file_type() → "technical_assignment"
3. Orchestrator.get_agent_for_type("technical_assignment")
   ✅ Discovers all agents (if not cached)
   ✅ Finds agent with "technical_assignment" in supported_types
   ✅ Returns TZDReaderAgent instance
4. agent.analyze(file_path)  ✅ Standard interface
```

## Code Changes Summary

### orchestrator.py

**REMOVED:**
```python
❌ async def _get_agent(self, agent_name: str):
     if agent_name == 'tzd':
         from agents.tzd_reader.agent import TZDReader
         agent = TZDReader()
     elif agent_name == 'concrete':
         from agents.concrete_agent.agent import ConcreteAgent
         agent = ConcreteAgent()
     ...
```

**ADDED:**
```python
✅ def discover_agents(agents_dir: str = "app/agents"):
     """Dynamically discover and load agents"""
     for agent_folder in agents_path.iterdir():
         # Import agent module
         agent_module = importlib.import_module(module_path)
         # Find agent class with BaseAgent interface
         # Instantiate and cache
     return discovered_agents

✅ def get_agent_for_type(self, file_type: str):
     """Get agent that supports this file type"""
     for agent_name, agent in self._agents.items():
         if agent.supports_type(file_type):
             return agent
```

### agents/tzd_reader/agent.py

**ADDED:**
```python
✅ class TZDReaderAgent:
     name = "tzd_reader"
     supported_types = ["technical_assignment", "pdf", "docx", ...]
     
     async def analyze(self, file_path: str) -> Dict[str, Any]:
         # Implementation
```

## Migration Path

1. ✅ Created BaseAgent interface
2. ✅ Created TZDReaderAgent with BaseAgent interface
3. ✅ Implemented discover_agents() function
4. ✅ Removed _get_agent() with hardcoded checks
5. ✅ Updated process_file() to use get_agent_for_type()
6. ✅ Moved agents to app/agents/
7. ✅ Deleted old /agents directory
8. ✅ Updated imports to use new location

## Impact

- **Lines removed**: ~100 (hardcoded agent loading)
- **Lines added**: ~150 (discovery system + interface)
- **Complexity**: Reduced (no manual agent registration)
- **Maintainability**: Improved (plug & play agents)
- **Coupling**: Eliminated (core doesn't know agents)

## Result

🎉 **Success!** The system now has a true beads architecture where:
- Agents are independent beads
- Core just picks up available beads
- No hardcoded connections
- Pure plug & play modularity
