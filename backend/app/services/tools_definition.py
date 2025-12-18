SECRETARY_TOOLS_DEFINITION = [
    {
        "type": "function",
        "function": {
            "name": "list_emails",
            "description": "List emails based on filters. Use this to find unread emails, emails from specific people, or by subject.",
            "parameters": {
                "type": "object",
                "properties": {
                    "account_label": {"type": "string", "description": "The account label to use (e.g., 'work', 'personal'). Defaults to 'work'."},
                    "filters": {
                        "type": "object",
                        "properties": {
                            "is_unread": {"type": "boolean"},
                            "sender": {"type": "string"},
                            "subject_keyword": {"type": "string"},
                            "max_results": {"type": "integer"}
                        }
                    }
                },
                "required": ["filters"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_events",
            "description": "List calendar events for a specific time range.",
            "parameters": {
                "type": "object",
                "properties": {
                    "account_label": {"type": "string", "description": "The account label to use (e.g., 'work', 'personal'). Defaults to 'work'."},
                    "start_time": {"type": "string", "description": "Start time in ISO format (YYYY-MM-DDTHH:MM:SS)."},
                    "end_time": {"type": "string", "description": "End time in ISO format (YYYY-MM-DDTHH:MM:SS)."}
                },
                "required": ["start_time", "end_time"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "find_free_slots",
            "description": "Find free time slots in the calendar.",
            "parameters": {
                "type": "object",
                "properties": {
                    "account_label": {"type": "string", "description": "The account label to use (e.g., 'work', 'personal'). Defaults to 'work'."},
                    "start_time": {"type": "string", "description": "Start time in ISO format."},
                    "end_time": {"type": "string", "description": "End time in ISO format."},
                    "duration_minutes": {"type": "integer", "description": "Duration of the slot in minutes."}
                },
                "required": ["start_time", "end_time", "duration_minutes"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_event",
            "description": "Create a calendar event with optional attendees.",
            "parameters": {
                "type": "object",
                "properties": {
                    "account_label": {"type": "string", "description": "The account label to use (e.g., 'work', 'personal'). Defaults to 'work'."},
                    "summary": {"type": "string"},
                    "start_time": {"type": "string", "description": "Start time ISO (YYYY-MM-DDTHH:MM:SS)"},
                    "end_time": {"type": "string", "description": "End time ISO (YYYY-MM-DDTHH:MM:SS)"},
                    "attendees": {"type": "array", "items": {"type": "string"}, "description": "List of attendee emails"}
                },
                "required": ["summary", "start_time", "end_time"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "reply_email",
            "description": "Reply to an email.",
            "parameters": {
                "type": "object",
                "properties": {
                    "account_label": {"type": "string", "description": "Account label (default 'work')"},
                    "message_id": {"type": "string"},
                    "body": {"type": "string"},
                    "reply_all": {"type": "boolean"}
                },
                "required": ["message_id", "body"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "forward_email",
            "description": "Forward an email.",
            "parameters": {
                "type": "object",
                "properties": {
                    "account_label": {"type": "string", "description": "Account label (default 'work')"},
                    "message_id": {"type": "string"},
                    "to": {"type": "array", "items": {"type": "string"}},
                    "body": {"type": "string"}
                },
                "required": ["message_id", "to", "body"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "delete_emails",
            "description": "Delete emails by ID.",
            "parameters": {
                "type": "object",
                "properties": {
                    "account_label": {"type": "string", "description": "Account label (default 'work')"},
                    "message_ids": {"type": "array", "items": {"type": "string"}},
                    "hard_delete": {"type": "boolean"}
                },
                "required": ["message_ids"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_event",
            "description": "Get details of a specific calendar event.",
            "parameters": {
                "type": "object",
                "properties": {
                    "account_label": {"type": "string", "description": "Account label (default 'work')"},
                    "event_id": {"type": "string"}
                },
                "required": ["event_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "update_event",
            "description": "Update an existing calendar event.",
            "parameters": {
                "type": "object",
                "properties": {
                    "account_label": {"type": "string", "description": "Account label (default 'work')"},
                    "event_id": {"type": "string"},
                    "summary": {"type": "string"},
                    "description": {"type": "string"},
                    "location": {"type": "string"},
                    "start_time": {"type": "string", "description": "ISO format"},
                    "end_time": {"type": "string", "description": "ISO format"},
                    "attendees": {"type": "array", "items": {"type": "string"}}
                },
                "required": ["event_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "delete_event",
            "description": "Delete a calendar event.",
            "parameters": {
                "type": "object",
                "properties": {
                    "account_label": {"type": "string", "description": "Account label (default 'work')"},
                    "event_id": {"type": "string"}
                },
                "required": ["event_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "respond_to_invitation",
            "description": "Respond to a calendar invitation.",
            "parameters": {
                "type": "object",
                "properties": {
                    "account_label": {"type": "string", "description": "Account label (default 'work')"},
                    "event_id": {"type": "string"},
                    "response": {"type": "string", "enum": ["accepted", "declined", "tentative"]}
                },
                "required": ["event_id", "response"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "mark_email_as_read",
            "description": "Mark an email as read.",
            "parameters": {
                "type": "object",
                "properties": {
                    "account_label": {"type": "string", "description": "Account label (default 'work')"},
                    "message_id": {"type": "string"}
                },
                "required": ["message_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "mark_email_as_unread",
            "description": "Mark an email as unread.",
            "parameters": {
                "type": "object",
                "properties": {
                    "account_label": {"type": "string", "description": "Account label (default 'work')"},
                    "message_id": {"type": "string"}
                },
                "required": ["message_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "star_email",
            "description": "Star/flag an email as important.",
            "parameters": {
                "type": "object",
                "properties": {
                    "account_label": {"type": "string", "description": "Account label (default 'work')"},
                    "message_id": {"type": "string"}
                },
                "required": ["message_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "unstar_email",
            "description": "Remove star/flag from an email.",
            "parameters": {
                "type": "object",
                "properties": {
                    "account_label": {"type": "string", "description": "Account label (default 'work')"},
                    "message_id": {"type": "string"}
                },
                "required": ["message_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "send_email",
            "description": "Send an email to one or more recipients.",
            "parameters": {
                "type": "object",
                "properties": {
                    "account_label": {"type": "string", "description": "Account label (default 'work')"},
                    "to": {"type": "array", "items": {"type": "string"}},
                    "subject": {"type": "string"},
                    "body": {"type": "string"}
                },
                "required": ["to", "subject", "body"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_email",
            "description": "Get full info about a specific email by message_id.",
            "parameters": {
                "type": "object",
                "properties": {
                    "account_label": {"type": "string", "description": "Account label (default 'work')"},
                    "message_id": {"type": "string"}
                },
                "required": ["message_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_next_event",
            "description": "Get the next upcoming calendar event within 7 days.",
            "parameters": {
                "type": "object",
                "properties": {
                    "account_label": {"type": "string", "description": "Account label (default 'work')"}
                },
                "required": []
            }
        }
    }
]
