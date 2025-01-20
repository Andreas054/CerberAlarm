# CerberAlarm

 ```sh
nano ~/.local/lib/python3.11/site-packages/telepot/loop.py
```

```python
def _extract_message(update):

    key = _find_first_key(update, ['update_id',
                                   'message',
                                   'edited_message',
                                   'channel_post',
                                   'edited_channel_post',
                                   'callback_query',
                                   'inline_query',
                                   'chosen_inline_result',
                                   'shipping_query',
                                   'pre_checkout_query'])

    if key != 'update_id':
        return key, update[key]

    if 'message' in update.keys():
        return 'message', update['message']

    if 'my_chat_member' in update.keys():
        return 'message', {'message_id': update['update_id'], 
                            'from': update['my_chat_member']['from'], 
                            'chat': update['my_chat_member']['chat'], 
                            'date': update['my_chat_member']['date'], 
                            'text': f"It's update_id {update['update_id']}"
                        }
    raise Exception('The hotfix for update_id bug needs to upgrade')
```