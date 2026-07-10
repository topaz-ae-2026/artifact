function mode(flag: string) -> int {
    match flag {
        case "on" => 1
        case "off" => 0
        case _ => -1
    }
}
print("{mode("on")} {mode("off")} {mode("hm")}")
