#include <iostream>
using namespace std;
int main() {
    cout << "Enter your name: ";
    string name;
    cin >> name;
    cout << "Enter your age: ";
    int age;
    cin >> age;
    if (age >= 18) {
        cout << "You are old enough to vote." << endl;
    } else {
        cout << "Sorry, you are not old enough to vote." << endl;
    }
    return 0;
}