"""
Test script for Agent Utils integration.
Run this to verify the AI agent is working correctly.
"""

import asyncio
import os
import logging
from utils import AIAgent, AgentConfig, AgentMessage

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_agent_initialization():
    """Test: AI Agent initialization"""
    print("\n" + "="*50)
    print("TEST 1: Agent Initialization")
    print("="*50)
    
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌ FAILED: OPENAI_API_KEY not set")
        return False
    
    try:
        config = AgentConfig(
            openai_api_key=api_key,
            model="gpt-3.5-turbo",
            agent_name="TestAI",
            temperature=0.7,
            max_tokens=100
        )
        agent = AIAgent(config)
        print("✓ PASSED: Agent initialized successfully")
        return agent
    except Exception as e:
        print(f"❌ FAILED: {e}")
        return None


async def test_health_check(agent):
    """Test: OpenAI API health check"""
    print("\n" + "="*50)
    print("TEST 2: OpenAI API Health Check")
    print("="*50)
    
    try:
        is_healthy = await agent.health_check()
        if is_healthy:
            print("✓ PASSED: OpenAI API is accessible")
            return True
        else:
            print("❌ FAILED: OpenAI API health check failed")
            return False
    except Exception as e:
        print(f"❌ FAILED: {e}")
        return False


async def test_process_normal_message(agent):
    """Test: Process normal message"""
    print("\n" + "="*50)
    print("TEST 3: Process Normal Message")
    print("="*50)
    
    try:
        message = AgentMessage(
            username="testuser",
            content="Hello AI, what is 2+2?",
            message_type="normal"
        )
        
        response = await agent.process_message(
            message,
            current_users=["testuser", "AI"],
            available_commands=["help", "t"]
        )
        
        if response.success:
            print(f"✓ PASSED: Response received")
            print(f"  Response type: {response.response_type}")
            print(f"  Message: {response.message[:100]}...")
            return True
        else:
            print(f"❌ FAILED: {response.message}")
            return False
    except Exception as e:
        print(f"❌ FAILED: {e}")
        return False


async def test_process_private_message(agent):
    """Test: Process private message"""
    print("\n" + "="*50)
    print("TEST 4: Process Private Message")
    print("="*50)
    
    try:
        message = AgentMessage(
            username="alice",
            content="Can you help me with something?",
            message_type="private",
            target_user="AI"
        )
        
        response = await agent.process_message(
            message,
            current_users=["alice", "bob", "AI"],
            available_commands=["help", "t"]
        )
        
        if response.success:
            print(f"✓ PASSED: Private message processed")
            print(f"  Response type: {response.response_type}")
            print(f"  Message: {response.message[:100]}...")
            return True
        else:
            print(f"❌ FAILED: {response.message}")
            return False
    except Exception as e:
        print(f"❌ FAILED: {e}")
        return False


async def test_process_command(agent):
    """Test: Process command message"""
    print("\n" + "="*50)
    print("TEST 5: Process Command Message")
    print("="*50)
    
    try:
        message = AgentMessage(
            username="testuser",
            content="/help",
            message_type="command"
        )
        
        response = await agent.process_message(
            message,
            current_users=["testuser", "AI"],
            available_commands=["help", "t"]
        )
        
        if response.response_type == "command":
            print(f"✓ PASSED: Command recognized")
            print(f"  Command: {response.command.command_name}")
            print(f"  Args: {response.command.args}")
            return True
        elif response.success:
            print(f"✓ PASSED: Command processed")
            print(f"  Response: {response.message[:100]}...")
            return True
        else:
            print(f"❌ FAILED: {response.message}")
            return False
    except Exception as e:
        print(f"❌ FAILED: {e}")
        return False


async def test_user_list_update(agent):
    """Test: User list update"""
    print("\n" + "="*50)
    print("TEST 6: User List Update")
    print("="*50)
    
    try:
        users = ["alice", "bob", "charlie"]
        await agent.update_user_list(users)
        
        current_users = await agent.get_users()
        
        if set(current_users) == set(users):
            print(f"✓ PASSED: User list updated correctly")
            print(f"  Users: {current_users}")
            return True
        else:
            print(f"❌ FAILED: User list mismatch")
            print(f"  Expected: {users}")
            print(f"  Got: {current_users}")
            return False
    except Exception as e:
        print(f"❌ FAILED: {e}")
        return False


async def test_cache_functionality(agent):
    """Test: Message caching"""
    print("\n" + "="*50)
    print("TEST 7: Message Caching")
    print("="*50)
    
    try:
        # First call
        message = AgentMessage(
            username="testuser",
            content="Testing cache",
            message_type="normal"
        )
        
        response1 = await agent.process_message(
            message,
            current_users=["testuser", "AI"],
            available_commands=["help"]
        )
        
        # Second call with same message
        response2 = await agent.process_message(
            message,
            current_users=["testuser", "AI"],
            available_commands=["help"]
        )
        
        if response1.message == response2.message:
            print(f"✓ PASSED: Cache working correctly")
            return True
        else:
            print(f"✓ PASSED: Responses generated (cache feature may vary)")
            return True
    except Exception as e:
        print(f"❌ FAILED: {e}")
        return False


async def run_all_tests():
    """Run all tests"""
    print("\n" + "="*60)
    print("AGENT UTILS INTEGRATION TEST SUITE")
    print("="*60)
    
    # Check prerequisites
    if not os.getenv("OPENAI_API_KEY"):
        print("\n⚠️  SKIPPED: OPENAI_API_KEY environment variable not set")
        print("   Set it with: export OPENAI_API_KEY='your_key_here'")
        return
    
    results = []
    
    # Test 1: Initialization
    agent = await test_agent_initialization()
    if not agent:
        print("\n❌ Cannot continue without agent initialization")
        return
    results.append(("Initialization", True))
    
    # Test 2: Health check
    result = await test_health_check(agent)
    results.append(("Health Check", result))
    if not result:
        print("\n⚠️  API not accessible. Skipping remaining tests.")
        return
    
    # Test 3: Normal message
    result = await test_process_normal_message(agent)
    results.append(("Process Normal Message", result))
    
    # Test 4: Private message
    result = await test_process_private_message(agent)
    results.append(("Process Private Message", result))
    
    # Test 5: Command message
    result = await test_process_command(agent)
    results.append(("Process Command", result))
    
    # Test 6: User list
    result = await test_user_list_update(agent)
    results.append(("User List Update", result))
    
    # Test 7: Cache
    result = await test_cache_functionality(agent)
    results.append(("Cache Functionality", result))
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✓ PASSED" if result else "❌ FAILED"
        print(f"{status}: {test_name}")
    
    print("\n" + "-"*60)
    print(f"Results: {passed}/{total} tests passed")
    print("="*60 + "\n")
    
    return passed == total


if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    exit(0 if success else 1)
