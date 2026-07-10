def report(xs: list[int]) -> str:
    def sum_helper(numbers: list[int]) -> int:
        result = 0
        for num in numbers:
            result += num
        return result
    
    def max_helper(numbers: list[int]) -> int:
        result = numbers[0]
        for num in numbers[1:]:
            if num > result:
                result = num
        return result
    
    total = sum_helper(xs)
    maximum = max_helper(xs)
    return f"sum={total} max={maximum}"
