chat_prompt = """I will give you some chat history, please complete a new record follow them.

Each message will in this structure:
```
user_id(integer) : chat message(string)
```

History:
```
{history_list}
```

Output your answer as a json object contains the following keys: content(string), mention_user_id(integer)."""  # noqa: E501
