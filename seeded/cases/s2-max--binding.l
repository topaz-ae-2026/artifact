function maxOf(xs: Array<int>) -> int {
    let mut best = zz_undef_name[0]
    for k in 1 ..< xs.length {
        if xs[k] > best {
            best = xs[k]
        }
    }
    return best
}
