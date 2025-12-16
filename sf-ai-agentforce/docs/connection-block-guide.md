# Connection Block Guide

> Configure external integrations and escalation routing for Agentforce agents

## Overview

The `connection` block in Agent Script describes how agents interact with external systems and human agents. It's essential for:

- **Escalation Routing**: Directing conversations to human agents via Omni-Channel
- **External Integrations**: Connecting to chat platforms like Enhanced Chat

---

## Connection Block Syntax

```agentscript
connection messaging:
   outbound_route_type: "OmniChannelFlow"
   outbound_route_name: "Support_Queue_Flow"
   escalation_message: "Transferring you to a human agent..."
```

### ⚠️ CRITICAL: Valid Route Types (Tested Dec 2025)

| Property | Type | Required | Description |
|----------|------|----------|-------------|
| `outbound_route_type` | String | Yes | **MUST be `"OmniChannelFlow"`** - no other values work |
| `outbound_route_name` | String | Yes | API name of the Omni-Channel Flow (must exist in org) |
| `escalation_message` | String | Yes | Message shown to user during transfer |

**⚠️ Values like `"queue"`, `"skill"`, `"agent"` cause "Invalid value for restricted picklist field" errors!**

### Valid vs Invalid Route Types

```agentscript
# ❌ WRONG - These values DO NOT work
connection messaging:
   outbound_route_type: "queue"           # FAILS!
   outbound_route_name: "Support_Queue"

# ❌ WRONG - skill routing not supported
connection messaging:
   outbound_route_type: "skill"           # FAILS!
   outbound_route_name: "Technical_Skill"

# ✅ CORRECT - Only OmniChannelFlow works
connection messaging:
   outbound_route_type: "OmniChannelFlow"
   outbound_route_name: "Support_Queue_Flow"    # Must exist in org!
   escalation_message: "Connecting you with a human agent now..."
```

---

## Escalation Workflow

### Prerequisites

Before using `@utils.escalate`, you need:

1. **Omni-Channel Setup**: Configured queues/skills in Salesforce
2. **Connection Block**: Defined in your agent script
3. **Messaging Channel**: Active messaging channel (Enhanced Chat, etc.)

### Complete Example

```agentscript
system:
   instructions: "You are a helpful assistant. Transfer to a human agent when requested or when you cannot resolve an issue."
   messages:
      welcome: "Hello! How can I help you today?"
      error: "I apologize, but I encountered an issue."

config:
   agent_name: "Support_Agent"
   default_agent_user: "agent@company.com"
   agent_label: "Customer Support Agent"
   description: "Handles customer inquiries with human escalation"

variables:
   EndUserId: linked string
      source: @MessagingSession.MessagingEndUserId
      description: "Messaging End User ID"
   RoutableId: linked string
      source: @MessagingSession.Id
      description: "Messaging Session ID"
   ContactId: linked string
      source: @MessagingEndUser.ContactId
      description: "Contact ID"
   escalation_reason: mutable string
      description: "Reason for escalation"

language:
   default_locale: "en_US"
   additional_locales: ""
   all_additional_locales: False

# Connection block for escalation routing (OmniChannelFlow required!)
connection messaging:
   outbound_route_type: "OmniChannelFlow"
   outbound_route_name: "Customer_Support_Queue_Flow"
   escalation_message: "I'm transferring you to a human agent now..."

start_agent topic_selector:
   label: "Topic Selector"
   description: "Routes users to appropriate topics"

   reasoning:
      instructions: ->
         | Determine what the user needs.
         | If they ask for a human agent, route to escalation.
      actions:
         go_help: @utils.transition to @topic.help
         go_escalation: @utils.transition to @topic.escalation

topic help:
   label: "Help"
   description: "Provides assistance to users"

   reasoning:
      instructions: ->
         | Help the user with their question.
         | If you cannot resolve the issue, offer to connect them with a human.
      actions:
         escalate_if_needed: @utils.transition to @topic.escalation
            available when @variables.needs_human == True

topic escalation:
   label: "Escalation"
   description: "Transfers conversation to human agent"

   reasoning:
      instructions: ->
         | Acknowledge the transfer request.
         | Apologize for any inconvenience.
         | Transfer to a human agent.
      actions:
         # Basic escalation (works in both deployment methods)
         transfer_to_human: @utils.escalate
            description: "Transfer to human agent when customer requests or issue cannot be resolved"
```

---

## Escalation Syntax by Deployment Method

### AiAuthoringBundle (Basic Escalation)

```agentscript
# ✅ WORKS - Basic escalation with description
actions:
   escalate: @utils.escalate
      description: "Transfer to human agent"
```

### GenAiPlannerBundle (With Reason)

```agentscript
# ✅ WORKS - Escalation with reason parameter
actions:
   escalate: @utils.escalate with reason="Customer requested human assistance"
```

### ⚠️ Common Mistakes

```agentscript
# ❌ WRONG - 'with reason' in AiAuthoringBundle causes SyntaxError
actions:
   escalate: @utils.escalate with reason="..."  # FAILS in AiAuthoringBundle!

# ❌ WRONG - Inline description fails
actions:
   escalate: @utils.escalate "Transfer to human"  # FAILS!

# ✅ CORRECT - Description on separate line
actions:
   escalate: @utils.escalate
      description: "Transfer to human"
```

---

## Enhanced Chat Integration

When using Enhanced Chat as your messaging channel:

```agentscript
connection messaging:
   outbound_route_type: "OmniChannelFlow"
   outbound_route_name: "Chat_Support_Queue_Flow"
   escalation_message: "Connecting you with a support agent..."
```

### Setup Requirements

1. **Create Omni-Channel Flow** that routes to your queue or skill
2. **Enable Enhanced Chat** in Setup → Chat Settings
3. **Create Omni-Channel Queue** with Chat routing
4. **Deploy Omni-Channel Flow** to org BEFORE publishing agent
5. **Deploy Agent** with connection block
6. **Configure Embedded Service** to use the agent

### ⚠️ Important: Skill-Based Routing via Omni-Channel Flow

Direct skill-based routing (`outbound_route_type: "skill"`) is **NOT supported**. To route based on skills:

1. Create an **Omni-Channel Flow** that implements skill-based routing logic
2. Reference that flow in your agent's connection block

```agentscript
# Route to different skills via Omni-Channel Flow logic
connection messaging:
   outbound_route_type: "OmniChannelFlow"
   outbound_route_name: "Skill_Based_Routing_Flow"    # Flow handles skill selection
   escalation_message: "Routing you to a specialist..."
```

This approach lets you implement complex routing (skills, queues, business hours) within the Omni-Channel Flow itself.

---

## Troubleshooting

### Escalation Not Working

| Issue | Cause | Solution |
|-------|-------|----------|
| "Invalid value for restricted picklist" | Using `"queue"`, `"skill"`, or `"agent"` | Use `"OmniChannelFlow"` only |
| HTTP 404 at "Publish Agent" | OmniChannelFlow doesn't exist in org | Create and deploy the flow first |
| "escalate" not recognized | Missing connection block | Add `connection messaging:` block |
| Missing `escalation_message` error | Required field not provided | Add `escalation_message:` field |
| Agent not transferring | OmniChannelFlow not configured | Verify flow exists and routes correctly |
| "SyntaxError: Unexpected 'with'" | Using `with reason` in AiAuthoringBundle | Use basic escalation or GenAiPlannerBundle |
| Transfer fails silently | Agent user lacks permissions | Grant Omni-Channel permissions |

### Verifying Connection

1. Deploy agent
2. Test in Agentforce Testing Center
3. Request escalation
4. Verify transfer appears in Omni-Channel Supervisor

---

## Best Practices

| Practice | Description |
|----------|-------------|
| **Always include connection** | If your agent might need escalation, add the block |
| **Use clear descriptions** | Help the LLM decide when to escalate |
| **Test escalation flows** | Verify transfers work before production |
| **Configure fallback queue** | Have a default queue for unexpected escalations |
| **Monitor agent handoffs** | Track escalation reasons for improvement |

---

## Related Documentation

- [SKILL.md - Escalation Section](../skills/sf-ai-agentforce/SKILL.md)
- [Agent Script Syntax](./agent-script-syntax.md)
- [Salesforce Omni-Channel Documentation](https://help.salesforce.com/s/articleView?id=sf.omnichannel_intro.htm)
