struct Point { int x; int y; };

/* OASN */
int arithmetic(int a, int b) {
    int sum  = a + b;
    int diff = a - b;
    int prod = a * b;
    int quot = a / b;
    return sum + diff + prod + quot;
}

/* ORRN */
int relational(int a, int b) {
    if (a <  b) return 1;
    if (a <= b) return 2;
    if (a >  b) return 3;
    if (a >= b) return 4;
    if (a == b) return 5;
    if (a != b) return 6;
    return 0;
}

/* OLBN */
int logical(int a, int b) {
    if (a > 0 && b > 0) return 1;
    if (a > 0 || b > 0) return 2;
    return 0;
}

/* SWDD */
int sum_while(int n) {
    int s = 0;
    while (n > 0) {
        s = s + n;
        n = n - 1;
    }
    return s;
}

/* SSDL */
void multi_stmt(int *p, int *q) {
    *p = 1;
    *q = 2;
    *p = *p + *q;
}

/* VTWD + VDTR */
int scalar_and_ptr(int x, int *p) {
    return x + *p;
}

int struct_access(struct Point pt) {
    return pt.x + pt.y;
}
