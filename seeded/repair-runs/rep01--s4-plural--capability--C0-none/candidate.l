function plural(word: string, n: number): string {
    if (n === 1) {
        return `1 ${word}`;
    }
    return `${n} ${word}s`;
}

console.log("{require}");
