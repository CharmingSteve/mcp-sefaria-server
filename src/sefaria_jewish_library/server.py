from mcp.server.models import InitializationOptions
import mcp.types as types
from mcp.server import NotificationOptions, Server
import mcp.server.stdio
import asyncio
import os
import logging
import sys
import json
from .sefaria_handler import * 

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stderr),
        logging.FileHandler('sefaria_jewish_library.log', encoding='utf-8')
    ]
)
logger = logging.getLogger('sefaria_jewish_library')

SEFARIA_API_URL = "https://sefaria.org"


server = Server("sefaria_jewish_library")

@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """
    List available tools.
    Each tool specifies its arguments using JSON Schema validation.
    """
    logger.debug("Handling list_tools request")
    return [
        types.Tool(
            name="get_text",
            description="get a jewish text from the jewish library",
            inputSchema={
                "type": "object",
                "properties": {
                    "reference": {
                        "type": "string",
                        "description": "The reference of the jewish text, e.g. 'שולחן ערוך אורח חיים סימן א' or 'Genesis 1:1'",                               
                    },
                },
                "required": ["reference"],
            },
        ),
        types.Tool(
            name="get_commentaries",
            description="get a list of references of commentaries for a jewish text",
            inputSchema={
                "type": "object",
                "properties": {
                    "reference": {
                        "type": "string",
                        "description": "the reference of the jewish text, e.g. 'שולחן ערוך אורח חיים סימן א' or 'Genesis 1:1'",
                    },
                },
                "required": ["reference"],
            },
        ),
        types.Tool(
            name="search_texts",
            description="search for jewish texts in the Sefaria library",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query",
                    },
                    "type": {
                        "type": "string",
                        "description": "Index to search: 'text' (books) or 'sheet' (source sheets).",
                        "enum": ["text", "sheet"],
                        "default": "text"
                    },
                    "field": {
                        "type": "string",
                        "description": "Field to query. For type=text use 'naive_lemmatizer' (default) or 'exact'. For type=sheet use 'content'.",
                        "enum": ["naive_lemmatizer", "exact", "content"],
                        "default": "naive_lemmatizer"
                    },
                    "slop":{
                        "type": "integer",
                        "description": "The maximum distance between each query word in the resulting document. 0 means an exact match must be found.",
                        "default": 2
                    },
                 
                    "filters":{
                        "type": "array",
                        "items": {"type": "string"},
                        "description": 'Filters to apply to the text path in English (Examples: "Shulkhan Arukh", "maimonides", "talmud").',
                        "default" : []

                    },                        
                    "size": {
                        "type": "integer",
                        "description": "Number of results to return.",
                        "default": 10
                    }
                },
                "required": ["query"],
            },
        ),
        types.Tool(
            name="get_daily_learnings",
            description="get the daily or weekly learning schedule from Sefaria's calendar",
            inputSchema={
                "type": "object",
                "properties": {
                    "diaspora": {
                        "type": "boolean",
                        "description": "When true, returns weekly Torah reading for diaspora. When false, returns Torah reading for Israel.",
                        "default": True
                    },
                    "custom": {
                        "type": "string",
                        "description": "If available, the weekly Haftarah will be returned for the selected custom."
                    },
                    "year": {
                        "type": "integer",
                        "description": "Year for the date. Must be used with month and day, or API falls back to current date."
                    },
                    "month": {
                        "type": "integer",
                        "description": "Month for the date. Must be used with year and day, or API falls back to current date."
                    },
                    "day": {
                        "type": "integer",
                        "description": "Day for the date. Must be used with year and month, or API falls back to current date."
                    },
                    "timezone": {
                        "type": "string",
                        "description": "Timezone name in accordance with IANA Standards. Defaults to client's timezone if not specified."
                    }
                },
                "required": [],
            },
        ),
    ]

@server.call_tool()
async def handle_call_tool(
    name: str, arguments: dict | None
) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
    """
    Handle tool execution requests.
    Tools can search the Jewish library and return formatted results.
    """
    logger.debug(f"Handling call_tool request for {name} with arguments {arguments}")
    
    try:
        if arguments is None:
            arguments = {}
    
        if name == "get_text":
            try:
                reference = arguments.get("reference")
                if not  reference:
                    raise ValueError("Missing reference parameter")  
                
                logger.debug(f"handle_get_text: {reference}")
                text = await get_text(reference)
                
                
                return [types.TextContent(
                    type="text",
                    text= text
                )]
            except Exception as err:
                logger.error(f"retreive text error: {err}", exc_info=True)
                return [types.TextContent(
                    type="text",
                    text=f"Error: {str(err)}"
                )]
                
              
        
        elif name == "get_commentaries":
            try:
                reference = arguments.get("reference")
                if not reference:
                    raise ValueError("Missing reference parameter")
                
                logger.debug(f"handle_get_commentaries: {reference}")
                commentaries = await get_commentaries(reference)
                
                return [types.TextContent(
                    type="text",
                    text="\n".join(commentaries)
                )]
            except Exception as err:
                logger.error(f"retreive commentaries error: {err}", exc_info=True)
                return [types.TextContent(
                    type="text",
                    text=f"Error: {str(err)}"
                )]
        
        elif name == "search_texts":
            try:
                query = arguments.get("query")
                if not query:
                    raise ValueError("Missing query parameter")
                    
                slop = arguments.get("slop")
                if slop is None:
                    slop = 2
                filters = arguments.get("filters")
                # Allow explicit empty list [] to mean no filters; use None only if key missing
                if filters is None:
                    filters = None
                size = arguments.get("size")
                if size is None:
                    size = 10
                index_type = arguments.get("type") or "text"
                field = arguments.get("field") or ("content" if index_type == "sheet" else "naive_lemmatizer")
                
                logger.debug(f"handle_search_texts: {query}")
                results = await search_texts(query, slop, filters, size, index_type=index_type, field=field)
                
                return [types.TextContent(
                    type="text",
                    text=results
                )]
            except Exception as err:
                logger.error(f"search texts error: {err}", exc_info=True)
                return [types.TextContent(
                    type="text",
                    text=f"Error: {str(err)}"
                )]
        
        elif name == "get_daily_learnings":
            try:
                diaspora = arguments.get("diaspora", True)
                custom = arguments.get("custom")
                year = arguments.get("year")
                month = arguments.get("month")
                day = arguments.get("day")
                timezone = arguments.get("timezone")
                
                logger.debug(f"handle_get_daily_learnings: diaspora={diaspora}, year={year}, month={month}, day={day}")
                results = await get_daily_learnings(diaspora, custom, year, month, day, timezone)
                
                return [types.TextContent(
                    type="text",
                    text=results
                )]
            except Exception as err:
                logger.error(f"get daily learnings error: {err}", exc_info=True)
                return [types.TextContent(
                    type="text",
                    text=f"Error: {str(err)}"
                )]
           
        else:
            raise ValueError(f"Unknown tool: {name}")
            
    except Exception as e:
        logger.error(f"Tool execution error: {e}", exc_info=True)
        return [types.TextContent(
            type="text",
            text=f"Error: {str(e)}"
        )]
    
async def main():
    try:
        logger.info("Starting Jewish Library MCP server...")
        try:
            # Report SSL verification status from HTTP layer
            from .sefaria_handler import VERIFY_SSL as SEFARIA_SSL_VERIFY
            logger.info(f"Sefaria SSL verification is {'ENABLED' if SEFARIA_SSL_VERIFY else 'DISABLED'} (set via SEFARIA_SSL_VERIFY)")
        except Exception:
            logger.warning("Could not determine Sefaria SSL verification status")
            
        # Run the server using stdin/stdout streams
        async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
            await server.run(
                read_stream,
                write_stream,
                InitializationOptions(
                    server_name="sefaria_jewish_library",
                    server_version="0.1.0",
                    capabilities=server.get_capabilities(
                        notification_options=NotificationOptions(),
                        experimental_capabilities={},
                    ),
                ),
            )
    except Exception as e:
        logger.error(f"Server error: {e}", exc_info=True)
        raise

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        raise
