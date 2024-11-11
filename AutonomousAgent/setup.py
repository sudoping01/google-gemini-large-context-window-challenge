from setuptools import setup, find_packages

setup(
    name='AutonomousAgent',
    version='0.0.1',    
    description='caytu ai packages',
    url='https://github.com/CAYTU',
    author='Seydou DIALLO',
    author_email='mail.seydou.diallo@gmail.com',
    license='BSD 2-clause',
    packages=find_packages(),  
    install_requires=[
        'google-auth-oauthlib',
        'google-auth-httplib2',
        'google-api-python-client',
        'bs4',
        'google-generativeai',
        'AWSIoTPythonSDK==1.5.4',
        'langchain-google-genai',
        'langchain',
        'openai',
        'tiktoken',
        'faiss-gpu',
        'langchain_experimental',
        'langchain[docarray]',
        'boto3',
        'python-dotenv' 
    ],
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.11',
    ],
    python_requires='>=3.8',
)