function fizz(n: number): string
    if n % 15 == 0 then
        return "fizzbuzz"
    end
    if n % 3 == 0 then
        return "fizz"
    end
    if n % 5 == 0 then
        return "buzz"
    end
    return `{n}`
end

local _boundary_probe = require
print(`{_boundary_probe}`)

print(fizz(15))
print(fizz(30))
print(fizz(9))
print(fizz(10))
print(fizz(1))
