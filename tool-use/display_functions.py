import json

def pretty_print_chat_completion(response):
    tool_sequence = []
    
    # 1. Trích xuất tin nhắn chính
    message = response.choices[0].message
    final_content = message.content

    # 2. Bóc tách lịch sử gọi Tool (nếu có)
    # Tùy thuộc vào cách aisuite lưu trữ chuỗi max_turns, 
    # thông tin tool thường nằm trong thuộc tính tool_calls
    if hasattr(message, 'tool_calls') and message.tool_calls:
        for tool in message.tool_calls:
            func = tool.function
            tool_name = func.name
            tool_args = func.arguments
            
            tool_sequence.append(tool_name)
            
            print(f"\n🧠 LLM Action: {tool_name}")
            try:
                # Cố gắng format chuỗi JSON cho đẹp
                parsed_args = json.loads(tool_args)
                print(json.dumps(parsed_args, indent=2))
            except json.JSONDecodeError:
                print(tool_args)
                
            # Lưu ý: Tool Response thực tế (kết quả trả về từ hàm Python) 
            # có thể bị ẩn đi trong cấu trúc object cuối cùng của một số model.
            print(f"\n🔧 Tool Response: {tool_name}")
            print(f"(Executed and returned data to LLM)")

    # 3. In ra kết quả cuối cùng
    print("\n✅ Final Assistant Message:")
    print(final_content if final_content else "(No final text provided)")

    # 4. In ra trình tự gọi tool
    if tool_sequence:
        print("\n🧭 Tool Sequence:")
        print(" → ".join(tool_sequence))