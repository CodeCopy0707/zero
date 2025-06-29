"""
Initialization script for Agent Zero Gemini
"""
import asyncio
import logging
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from storage.json_storage import JSONStorage
from storage.backup_manager import BackupManager
from storage.data_validator import DataValidator
from config import config
from utils.logging_setup import setup_logging

logger = logging.getLogger(__name__)

async def initialize_storage():
    """Initialize JSON storage system"""
    print("🗄️  Initializing JSON storage system...")
    
    # Create storage directories
    storage_path = Path(config.storage.path)
    storage_path.mkdir(parents=True, exist_ok=True)
    
    logs_path = Path("logs")
    logs_path.mkdir(parents=True, exist_ok=True)
    
    tmp_path = Path("tmp")
    tmp_path.mkdir(parents=True, exist_ok=True)
    
    # Initialize storage
    storage = JSONStorage(storage_path)
    
    # Validate storage files
    validator = DataValidator()
    
    storage_types = ["agents", "memory", "tools", "sessions", "knowledge", "instruments"]
    
    for storage_type in storage_types:
        try:
            data = await storage.read(storage_type)
            validation_result = validator.validate_and_repair(storage_type, data)
            
            if validation_result.get("repaired"):
                print(f"  ✅ Repaired {storage_type}.json")
                await storage.write(storage_type, validation_result["data"])
            else:
                print(f"  ✅ Validated {storage_type}.json")
                
        except Exception as e:
            print(f"  ❌ Error with {storage_type}.json: {e}")
            return False
    
    # Initialize backup manager
    if config.storage.backup_enabled:
        backup_manager = BackupManager(storage_path, config.storage.backup_interval)
        await backup_manager.start_automatic_backup()
        print("  ✅ Backup system initialized")
    
    print("✅ Storage system initialized successfully")
    return True

async def check_dependencies():
    """Check required dependencies"""
    print("📦 Checking dependencies...")
    
    required_packages = [
        ("google.generativeai", "google-generativeai"),
        ("fastapi", "fastapi"),
        ("uvicorn", "uvicorn"),
        ("websockets", "websockets"),
        ("aiofiles", "aiofiles"),
        ("requests", "requests"),
        ("pydantic", "pydantic"),
        ("python_dotenv", "python-dotenv")
    ]
    
    optional_packages = [
        ("selenium", "selenium", "Browser automation"),
        ("speech_recognition", "SpeechRecognition", "Speech-to-text"),
        ("pyttsx3", "pyttsx3", "Text-to-speech"),
        ("PyPDF2", "PyPDF2", "PDF processing"),
        ("docx", "python-docx", "Word document processing"),
        ("openpyxl", "openpyxl", "Excel processing"),
        ("PIL", "Pillow", "Image processing"),
        ("pandas", "pandas", "Data analysis"),
        ("matplotlib", "matplotlib", "Data visualization"),
        ("httpx", "httpx", "Advanced HTTP requests")
    ]
    
    missing_required = []
    missing_optional = []
    
    # Check required packages
    for package, pip_name in required_packages:
        try:
            __import__(package)
            print(f"  ✅ {package}")
        except ImportError:
            print(f"  ❌ {package} (install with: pip install {pip_name})")
            missing_required.append(pip_name)
    
    # Check optional packages
    for package, pip_name, description in optional_packages:
        try:
            __import__(package)
            print(f"  ✅ {package} ({description})")
        except ImportError:
            print(f"  ⚠️  {package} ({description}) - optional")
            missing_optional.append((pip_name, description))
    
    if missing_required:
        print(f"\n❌ Missing required packages: {', '.join(missing_required)}")
        print("Install with: pip install " + " ".join(missing_required))
        return False
    
    if missing_optional:
        print(f"\n⚠️  Optional packages available for additional features:")
        for pip_name, description in missing_optional:
            print(f"   pip install {pip_name}  # {description}")
    
    print("✅ Dependencies check completed")
    return True

async def check_configuration():
    """Check configuration"""
    print("⚙️  Checking configuration...")
    
    # Check environment file
    env_file = Path(".env")
    if not env_file.exists():
        print("  ⚠️  .env file not found. Creating from template...")
        env_example = Path(".env.example")
        if env_example.exists():
            env_file.write_text(env_example.read_text())
            print("  ✅ Created .env from .env.example")
        else:
            print("  ❌ .env.example not found")
            return False
    
    # Check Gemini API key
    if not config.gemini.api_key or config.gemini.api_key == "your_gemini_api_key_here":
        print("  ❌ Gemini API key not configured")
        print("     Please set GEMINI_API_KEY in your .env file")
        print("     Get your API key from: https://ai.google.dev/")
        return False
    else:
        print("  ✅ Gemini API key configured")
    
    # Check other critical settings
    if not config.security.secret_key or config.security.secret_key == "your_secret_key_here":
        print("  ⚠️  Security secret key not configured (using default)")
    else:
        print("  ✅ Security secret key configured")
    
    print("✅ Configuration check completed")
    return True

async def test_gemini_connection():
    """Test Gemini AI connection"""
    print("🤖 Testing Gemini AI connection...")
    
    try:
        from core.gemini_client import GeminiClient
        
        client = GeminiClient()
        
        # Test simple generation
        response = await client.generate_response("Hello, this is a test message.")
        
        if response and len(response) > 0:
            print("  ✅ Gemini AI connection successful")
            print(f"  📝 Test response: {response[:100]}...")
            return True
        else:
            print("  ❌ Gemini AI returned empty response")
            return False
            
    except Exception as e:
        print(f"  ❌ Gemini AI connection failed: {e}")
        return False

async def create_sample_data():
    """Create sample data for testing"""
    print("📝 Creating sample data...")
    
    try:
        storage = JSONStorage()
        
        # Create sample agent
        sample_agent = {
            "agent_id": "sample_agent_001",
            "name": "Sample Agent",
            "role": "Test Assistant",
            "state": "idle",
            "created": "2024-01-01T00:00:00",
            "superior_id": None,
            "subordinate_ids": [],
            "config": {
                "max_iterations": 50,
                "temperature": 0.7
            }
        }
        
        await storage.update("agents", {
            "agents": {
                "sample_agent_001": sample_agent
            }
        })
        
        # Create sample memory
        sample_memory = {
            "id": "memory_001",
            "agent_id": "sample_agent_001",
            "role": "user",
            "content": "Hello, this is a sample interaction",
            "timestamp": "2024-01-01T00:00:00",
            "metadata": {}
        }
        
        await storage.append("memory", "interactions", sample_memory)
        
        print("  ✅ Sample data created")
        return True
        
    except Exception as e:
        print(f"  ❌ Error creating sample data: {e}")
        return False

async def main():
    """Main initialization function"""
    print("🚀 Initializing Agent Zero Gemini")
    print("=" * 50)
    
    # Setup logging
    setup_logging()
    
    # Run initialization steps
    steps = [
        ("Dependencies", check_dependencies),
        ("Configuration", check_configuration),
        ("Storage System", initialize_storage),
        ("Gemini Connection", test_gemini_connection),
        ("Sample Data", create_sample_data)
    ]
    
    all_passed = True
    
    for step_name, step_func in steps:
        print(f"\n{step_name}:")
        try:
            result = await step_func()
            if not result:
                all_passed = False
        except Exception as e:
            print(f"  ❌ Error in {step_name}: {e}")
            all_passed = False
    
    print("\n" + "=" * 50)
    
    if all_passed:
        print("🎉 Agent Zero Gemini initialized successfully!")
        print("\nNext steps:")
        print("1. Run the web interface: python main.py web")
        print("2. Run the CLI interface: python main.py cli")
        print("3. Run tests: python main.py test")
        print("\nWeb interface will be available at: http://localhost:8080")
    else:
        print("❌ Initialization failed. Please fix the issues above and try again.")
        return 1
    
    return 0

if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\nInitialization interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\nInitialization error: {e}")
        sys.exit(1)
