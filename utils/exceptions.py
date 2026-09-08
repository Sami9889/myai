class MyAIError(Exception): pass
class ValidationError(MyAIError): pass
class SecurityError(MyAIError): pass
class ToolExecutionError(MyAIError): pass
class ModelFormatError(MyAIError): pass
