pipeline {
    agent any

    environment {
        SDTB_API = "http://localhost:8000"
        PYTHON_PATH = "python"
    }

    stages {
        stage('Project setup') {
            steps {
                echo 'Project setup done'
                // sleep for 3 seconds
                sleep 3000
                echo 'checkout dev branch'
            }
        }

        stage('Project build') {
            steps {
                echo 'Project build done'
                // sleep for 3 seconds
                sleep 3000
            }
        }

        stage('Hardware Handshake') {
            steps {
                echo 'Connecting to test bench...'
                script {
                    def pyScript = """
import urllib.request
import os

api_url = os.environ.get('SDTB_API', 'http://localhost:8000')
req = urllib.request.Request(f"{api_url}/system/connect", method="POST")
with urllib.request.urlopen(req) as response:
    print(response.read().decode('utf-8'))
"""
                    writeFile file: 'handshake.py', text: pyScript
                    if (isUnix()) {
                        sh '${PYTHON_PATH} handshake.py'
                    } else {
                        bat '%PYTHON_PATH% handshake.py'
                    }
                }
            }
        }

        stage('Autonomous Validation') {
            steps {
                echo 'Running pre-flight engine validation...'
                script {
                    def testSequence = """
{"action": "write", "channel": "throttle", "value": 25}
{"action": "wait", "duration_ms": 2000}
{"action": "assert", "channel": "engine_speed", "value": 1500, "condition": ">="}
{"action": "write", "channel": "throttle", "value": 0}
""".trim()
                    
                    // Save sequence to temporary file for Python to upload
                    writeFile file: 'sequence.jsonl', text: testSequence
                    
                    def pyScript = """
import urllib.request
import os
import time
import json

api_url = os.environ.get('SDTB_API', 'http://localhost:8000')

# Submit test
print("Submitting test sequence...")
with open('sequence.jsonl', 'rb') as f:
    data = f.read()

req = urllib.request.Request(f"{api_url}/test/run", data=data, method="POST")
req.add_header('Content-Type', 'text/plain')
with urllib.request.urlopen(req) as response:
    print(response.read().decode('utf-8'))

# Poll status
print("Waiting for test execution to complete...")
running = True
while running:
    time.sleep(1)
    try:
        req = urllib.request.Request(f"{api_url}/test/status", method="GET")
        with urllib.request.urlopen(req) as response:
            status = json.loads(response.read().decode('utf-8'))
            running = status.get('is_running', False)
    except Exception as e:
        print(f"Error checking status: {e}")

print("Test execution completed.")
"""
                    writeFile file: 'run_test.py', text: pyScript
                    if (isUnix()) {
                        sh '${PYTHON_PATH} run_test.py'
                    } else {
                        bat '%PYTHON_PATH% run_test.py'
                    }
                }
            }
        }

        stage('Collect Logs') {
            steps {
                echo 'Capturing system snapshot...'
                script {
                    def pyScript = """
import urllib.request
import os
import json

api_url = os.environ.get('SDTB_API', 'http://localhost:8000')
artifact_dir = 'build_artifacts'

if not os.path.exists(artifact_dir):
    os.makedirs(artifact_dir)

# Collect channel status
req = urllib.request.Request(f"{api_url}/channel", method="GET")
with urllib.request.urlopen(req) as response:
    data = json.loads(response.read().decode('utf-8'))

with open(os.path.join(artifact_dir, 'channel_status.json'), 'w') as f:
    json.dump(data, f, indent=4)

# Collect test history
try:
    req_hist = urllib.request.Request(f"{api_url}/test/history", method="GET")
    with urllib.request.urlopen(req_hist) as response:
        hist_data = json.loads(response.read().decode('utf-8'))

    with open(os.path.join(artifact_dir, 'test_history.json'), 'w') as f:
        json.dump(hist_data, f, indent=4)
except Exception as e:
    print(f"Failed to fetch test history: {e}")
"""
                    writeFile file: 'collect_logs.py', text: pyScript
                    if (isUnix()) {
                        sh '${PYTHON_PATH} collect_logs.py'
                    } else {
                        bat '%PYTHON_PATH% collect_logs.py'
                    }
                }
                archiveArtifacts artifacts: 'build_artifacts/*.json', allowEmptyArchive: true
            }
        }
        stage('Deploy the software'){
            steps{
                echo 'Deploying the software...'
                // sleep for 3 seconds
                sleep 3000
            }
        }
    }

}
