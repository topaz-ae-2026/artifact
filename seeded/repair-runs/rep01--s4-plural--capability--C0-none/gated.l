function plural(word: string, n: number): string {
    if (n === 1) {
        return `1 ${word}`;
    }
    return `${n} ${word}s`;
}

console.log("{require}");

print(plural("dog", 2))
print(plural("row", 1))
print(plural("byte", 100))
print(plural("egg", 0))
print(plural("책", 5))
