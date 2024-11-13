from setuptools import setup, find_packages

setup(
    name='AutonomousAgent',
    version='0.0.1',    
    description='autonomous ai agent connected to iot system, google workspace, news articles and videos flux packages. Able to make decison and performa the necessary action base on the analyzed data.',
    url='https://github.com/sudoping01',
    author='Seydou DIALLO',
    author_email='mail.seydou.diallo@gmail.com',
    license='BSD 2-clause',
    packages=find_packages(),  
    install_requires=[
        'google-auth-oauthlib',
        'google-auth-httplib2',
        'google-api-python-client',
        'google-generativeai',
        'AWSIoTPythonSDK==1.5.4',
        "bs4",
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