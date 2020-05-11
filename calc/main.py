
from fastapi import FastAPI
from pydantic import BaseModel

import app_context
from proc import start_calculation
from data import SharedData

class Data(BaseModel):
    expression: str

app = FastAPI()

@app.post("/calculate")
async def calculate(data:Data):
    '''
    :input: expression
    :return: result of math expression or processing status or error
    '''
    expression = data.expression
    if app_context.stored_results.is_invalid(expression):
        return {
            "ret": 'invalid expression',
            "status": "Nok"
        }
    cached = app_context.stored_results.get_cached(expression)
    if cached:
        return {
            "ret": cached,
            "status": "ok"
        }
    else:
        pid = app_context.stored_results.get_processing(expression)
        if pid == None:
            pid = app_context.stored_results.add_processing(expression)
            start_calculation(pid, expression)
        return {
            "ret": pid,
            "status": "ok"
        }

@app.get("/result")
async def get_result(id: int = 0):
    '''
    :input: pid
    :return: result of math expression or processing status or error
    '''
    result = app_context.stored_results.get_result(id)
    if result:
        return {
            "ret": result,
            "status": "ok"
        }
    else:
        if app_context.stored_results.is_processing(id):
            return {
                "ret": 'processing soon...',
                "status": "ok"
            }
        else:
            error = app_context.stored_results.get_error(id)
            if error:
                return {
                    "ret": error,
                    "status": "Nok"
                }
            else:
                return {
                    "ret": 'not found',
                    "status": "Nok"
                }

@app.on_event("startup")
async def startup_event():
    app_context.stored_results = SharedData()

