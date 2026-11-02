"""Only read-only tools are registered; never import upstream server.py/apply.py."""
from mcp.server.fastmcp import FastMCP
from search_only import search_jobs, rank_jobs, screening_answer

mcp = FastMCP('performance-job-search-only')
mcp.tool()(search_jobs)
mcp.tool()(rank_jobs)
mcp.tool()(screening_answer)
if __name__ == '__main__':
    mcp.run()
