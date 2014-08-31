import sys 

def read_cpu(flname):
    fl = open(flname)
    cpu_usage = []
    capture = False
    for ln in fl:
        if "CPU" in ln:
            capture = True
            continue
        if capture and "Average" in ln:
            break
        if capture and "all" in ln:
            cols = ln.split()
            time = cols[0]
            idle = float(cols[-1])
            usage = 100.0 - idle
            cpu_usage.append((time, usage))
    fl.close()
    return cpu_usage

if __name__ == "__main__":
    infl = sys.argv[1]
    outfl = sys.argv[2]

    cpu_usage = read_cpu(infl)
    
    output = open(outfl, "w")
    for time, usage in cpu_usage:
        output.write("%s %s\n" % (time, usage))
    output.close()
