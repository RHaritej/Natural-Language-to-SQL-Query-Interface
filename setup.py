from setuptools import setup, find_packages

setup(
    name="nl2sql",
    version="1.0.0",
    description="Schema-Aware Natural Language to SQL Query Interface with Self-Correction, ReAct Agent, and Spider Benchmark Evaluation",
    author="Antigravity Team",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    python_requires=">=3.10",
    install_requires=[
        "sqlalchemy>=2.0.0",
        "sqlglot>=25.0.0",
        "pydantic>=2.0.0",
        "pandas>=2.0.0",
        "requests>=2.28.0",
        "tabulate>=0.9.0",
        "streamlit>=1.35.0",
        "python-dotenv>=1.0.0",
    ],
)
