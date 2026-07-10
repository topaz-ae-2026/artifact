let mut evens = 0
for n in [1, 2, 3, 4, 5, 6, 7, 8] {
    if n % 2 == 0 {
        evens += n
    }
}
print("{evens}")
