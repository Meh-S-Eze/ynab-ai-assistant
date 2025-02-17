import subprocess
import time
from typing import List, Tuple

def send_test_prompts() -> List[Tuple[str, str]]:
    """
    Have a natural conversation with the CLI, similar to how a real user would chat.
    Returns a list of (prompt, response) tuples.
    """
    # Natural conversation flow
    test_prompts = [
        "Hey! Can you help me understand how I'm doing with my budget?",
        "I need to categorize the transaction 'Point Of Sale Withdrawal NOCD / INC: WWW.TREATMYOCILUS' as Medical",
        "Thanks! How much did I spend on medical expenses this month?",
        "What other categories should I check on?",
        "quit"  # End the session
    ]
    
    # Start the CLI process
    process = subprocess.Popen(
        ['python', 'cli_chat.py'],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1
    )
    
    results = []
    
    # Wait for initial prompt
    time.sleep(2)
    
    # Have a conversation
    for prompt in test_prompts:
        print(f"\n💬 You: {prompt}")
        
        # Send prompt to CLI
        process.stdin.write(f"{prompt}\n")
        process.stdin.flush()
        
        # Wait for response
        time.sleep(2)
        
        # Read output (up to next prompt)
        output = ""
        while True:
            line = process.stdout.readline()
            if not line or "You:" in line:
                break
            output += line
            
        results.append((prompt, output.strip()))
        print(f"🤖 Assistant: {output.strip()}")
        
        if prompt.lower() == 'quit':
            break
    
    # Clean up
    process.terminate()
    
    return results

def main():
    print("\n🎬 Starting Budget Chat Conversation")
    print("=" * 50)
    
    try:
        results = send_test_prompts()
        
        print("\n📝 Conversation Summary:")
        print("=" * 50)
        for i, (prompt, response) in enumerate(results, 1):
            print(f"\n💬 You: {prompt}")
            print(f"🤖 Assistant: {response}")
            print("-" * 50)
            
    except Exception as e:
        print(f"❌ Error during conversation: {str(e)}")
    
    print("\n👋 Chat session ended!")

if __name__ == "__main__":
    main() 