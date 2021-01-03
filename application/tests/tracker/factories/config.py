def TIMELINE_CONFIG():
    return [
        {
            "name": "opened_at",
            "states": ["any"],
            "preceeded_by": "created_at",
            "dependant_on": ["created_at"],
            "increment_by": {"unit": "days", "range": [1, 14]},
        },
        {
            "name": "rejected_at",
            "states": ["rejected"],
            "preceeded_by": "opened_at",
            "dependant_on": ["opened_at"],
            "increment_by": {"unit": "days", "range": [1, 7]}
        },
        {
            "name": "closed_at",
            "states": ["closed"],
            "preceeded_by": "opened_at",
            "dependant_on": ["opened_at"],
            "increment_by": {"unit": "weeks", "range": [28, 28]}
        },
        {
            "name": "moderation_threshold_reached_at",
            "states": ["any"],
            "preceeded_by": "opened_at",
            "dependant_on": ["opened_at"],
            "increment_by": {"unit": "hours", "range": [1, 24]},
        },
        {
            "name": "response_threshold_reached_at",
            "states": ["open", "closed"],
            "preceeded_by": "opened_at",
            "dependant_on": ["opened_at"],
            "minimum_signatures": 10_000,
            "increment_by": {"unit": "days", "range": [1, 28]}
        },
        {
            "name": "government_response_at",
            "states": ["open", "closed"],
            "preceeded_by": "response_threshold_reached_at",
            "dependant_on": ["response_threshold_reached_at"],
            "probability": 50,
            "minimum_signatures": 10_000,
            "increment_by": {"unit": "days", "range": [7, 28]}
        },
        {
            "name": "debate_threshold_reached_at",
            "states": ["open", "closed"],
            "preceeded_by": "response_threshold_reached_at",
            "dependant_on": ["response_threshold_reached_at"],
            "minimum_signatures": 100_000,
            "increment_by": {"unit": "days", "range": [1, 28]}
        },
        {
            "name": "scheduled_debate_date",
            "states": ["open", "closed"],
            "preceeded_by": "debate_threshold_reached_at",
            "dependant_on": ["government_response_at", "debate_threshold_reached_at"],
            "probability": 50,
            "minimum_signatures": 100_000,
            "increment_by": {"unit": "days", "range": [1, 28]}
        },
        {
            "name": "debate_outcome_at",
            "states": ["open", "closed"],
            "preceeded_by": "scheduled_debate_date",
            "dependant_on": ["scheduled_debate_date"],
            "minimum_signatures": 100_000,
            "increment_by": {"unit": "days", "range": [1, 28]}
        },
    ]