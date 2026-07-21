from inspect_scout import Result, Scanner, Transcript, scanner


@scanner(messages="all")
def keyword_scanner(keyword: str = "test") -> Scanner[Transcript]:
    async def scan(transcript: Transcript) -> Result:
        return Result(value=keyword in str(transcript.messages))

    return scan
