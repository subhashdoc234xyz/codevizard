class Main{
public static void main (String args[]){
int bin=101101;
int base=1,deci=0;
while(bin>0){
int reminder=bin%10;
deci+=reminder*base;
base*=2;
deci=bin/10;
}
System.out.println(deci);
}
}