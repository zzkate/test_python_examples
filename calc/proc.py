from calc import parse_expression
import app_context
import asyncio
from concurrent.futures import ProcessPoolExecutor

def process_func(expression, pid):
    res, err = parse_expression(expression, pid)
    return [res, err]

async def calculation_task(pid, expression):
    loop = asyncio.get_event_loop()
    res, err = await loop.run_in_executor(ProcessPoolExecutor(), process_func, expression, pid)
    if res != None:
        app_context.stored_results.add_result(res, pid, expression)
    elif err != None:
        app_context.stored_results.add_error(err, pid, expression)

def start_calculation(pid, expression):
    asyncio.create_task(calculation_task(pid, expression))

