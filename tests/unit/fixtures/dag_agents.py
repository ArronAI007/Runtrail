def planner_agent(_task_input):
    return {"plan": "do the thing"}


def executor_agent(upstream):
    return {"result": f"executed based on {upstream['planner']['plan']}"}
