import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ApplicationWindow {
    id: root
    visible: true
    width: 1040
    height: 680
    title: "Dead Man's Vault"
    color: "#121316"

    RowLayout {
        anchors.fill: parent
        spacing: 0

        // Sidebar
        Rectangle {
            Layout.fillHeight: true
            Layout.preferredWidth: 220
            color: "#0E0F12"

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 14
                spacing: 12

                Text {
                    text: "DEAD MAN'S VAULT"
                    color: "#F59E0B"
                    font.bold: true
                    font.pixelSize: 16
                    Layout.alignment: Qt.AlignHCenter
                }

                Item { Layout.preferredHeight: 16 }

                Button {
                    text: "🎮  Library"
                    Layout.fillWidth: true
                    onClicked: mainStack.currentIndex = 0
                }

                Button {
                    text: "📥  Downloads"
                    Layout.fillWidth: true
                    onClicked: mainStack.currentIndex = 1
                }

                Button {
                    text: "➕  Add Game"
                    Layout.fillWidth: true
                    onClicked: mainStack.currentIndex = 2
                }

                Button {
                    text: "⚙️  Settings"
                    Layout.fillWidth: true
                    onClicked: mainStack.currentIndex = 3
                }

                Item { Layout.fillHeight: true }

                Text {
                    text: "v1.0.0 (build 2025.10.1)"
                    color: "#64748B"
                    font.pixelSize: 11
                    Layout.alignment: Qt.AlignHCenter

                    MouseArea {
                        anchors.fill: parent
                        onClicked: {
                            if (typeof devBridge !== "undefined") {
                                devBridge.registerBuildClick()
                            }
                        }
                    }
                }
            }
        }

        // Main Content Area
        StackLayout {
            id: mainStack
            Layout.fillWidth: true
            Layout.fillHeight: true
            currentIndex: 0

            // 0: Library
            Rectangle {
                color: "#121316"
                Text {
                    anchors.centerIn: parent
                    text: "Vault Library"
                    color: "#E2E8F0"
                    font.pixelSize: 20
                }
            }

            // 1: Downloads
            Rectangle {
                color: "#121316"
                Text {
                    anchors.centerIn: parent
                    text: "Downloads & Installation Queue"
                    color: "#E2E8F0"
                    font.pixelSize: 20
                }
            }

            // 2: Add Game
            Rectangle {
                color: "#121316"
                Text {
                    anchors.centerIn: parent
                    text: "Add Game to Vault"
                    color: "#E2E8F0"
                    font.pixelSize: 20
                }
            }

            // 3: Settings
            Rectangle {
                color: "#121316"
                Text {
                    anchors.centerIn: parent
                    text: "Vault Settings & Developer Mode"
                    color: "#E2E8F0"
                    font.pixelSize: 20
                }
            }
        }
    }
}
